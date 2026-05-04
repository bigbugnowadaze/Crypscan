"""Spike-9B decoder: image-space NCC + multi-pilot calibration.

Implements ADDENDUM_06 pillars 1-3:
  1. σ=8 / half_size=24 germs (channel-matched scale; encoder-side)
  2. Image-space NCC against 256 pre-rendered templates (no LSQ fit;
     decode metric is projection magnitude)
  3. Spatially-distributed multi-pilot fit: 2×2 quadrant tiling, each
     quadrant gets its own (a, b, γ) intensity transform from the 4
     pilots in that quadrant.

Pipeline:
    PNG -> read 8-bit grayscale -> ArUco pose (unchanged) -> rectify
    -> for each of 16 distributed pilots: gather true patch + observed
       pixels; bucket by canvas quadrant (4 pilots per quadrant) ->
       fit 4 (a,b,γ) transforms, one per quadrant
    -> for each germ position:
       extract 49×49 patch from rectified-corrected image (using
       per-quadrant transform)
       NCC against all 256 pre-rendered templates
       pick max -> codeword index -> byte
    -> RS + AXP6 + Brotli + SHA-256
"""
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
import hashlib
import json

import brotli
import numpy as np
from PIL import Image

from header import parse_header
from basis import OrthoBasis
from ecc import rs_decode
from codebook import design_codebook
from pilots import (
    select_anchor_codewords, gather_anchor_pixels,
    fit_intensity_transform, fit_local_intensity_transforms,
    LocalIntensityTransformGrid, IntensityTransform,
)
from manifest import parse_manifest_bytes, MANIFEST_GERM_COUNT
from fiducials import canonical_layout
from pose import detect_pose, rectify
from encoder import (
    CANVAS_WIDTH, CANVAS_HEIGHT, GRID_SLOTS,
    MANIFEST_INDICES, PILOT_INDICES, PAYLOAD_INDICES, PAYLOAD_CAPACITY,
    EncodeParams, grid_index_to_pixel, N_PILOTS,
)
from discrete_codebook import render_codebook_patches, classify_patch


@dataclass
class DecodeResult:
    filename: str
    payload: bytes
    sha256: bytes
    sha256_ok: bool
    size_ok: bool
    n_payload_germs: int
    pose_ok: bool
    pilot_calibration: str         # 'global' or 'per-quadrant'
    n_pilots_per_quadrant: list    # how many pilots fell in each quadrant
    decode_error: str | None
    median_manifest_ncc: float
    median_payload_ncc: float
    rs_corrected_frames: int
    rs_failed_frames: list


def _read_image(png_path: Path) -> np.ndarray:
    img = Image.open(png_path)
    arr = np.asarray(img)
    if img.mode == 'L':
        return arr.astype(np.float32) / 255.0
    if img.mode in ('I;16', 'I'):
        return arr.astype(np.float32) / 65535.0
    return np.asarray(img.convert('L'), dtype=np.float32) / 255.0


def _empty(error: str, pose_ok: bool = False) -> DecodeResult:
    return DecodeResult(
        filename='', payload=b'', sha256=b'',
        sha256_ok=False, size_ok=False, n_payload_germs=0,
        pose_ok=pose_ok, pilot_calibration='', n_pilots_per_quadrant=[],
        decode_error=error,
        median_manifest_ncc=0.0, median_payload_ncc=0.0,
        rs_corrected_frames=0, rs_failed_frames=[],
    )


def _extract_patch(image: np.ndarray, cx: int, cy: int, half_size: int) -> np.ndarray:
    side = 2 * half_size + 1
    x0 = cx - half_size; x1 = cx + half_size + 1
    y0 = cy - half_size; y1 = cy + half_size + 1
    if x0 < 0 or y0 < 0 or x1 > image.shape[1] or y1 > image.shape[0]:
        return np.full((side, side), 0.5, dtype=np.float32)
    return image[y0:y1, x0:x1].astype(np.float32)


def decode(png_path: Path,
              params: EncodeParams | None = None,
              use_per_quadrant_calibration: bool = True) -> DecodeResult:
    """Decode a spike-9B carrier."""
    if params is None:
        params = EncodeParams()
    png_path = Path(png_path)
    captured = _read_image(png_path)

    basis = OrthoBasis.build(params.half_size, params.sigma)
    codebook = design_codebook(
        basis, n_codewords=params.n_codewords, seed=params.codebook_seed,
    )
    templates = render_codebook_patches(codebook, basis,
                                          amp=params.amp,
                                          baseline=params.baseline)
    layout = canonical_layout(CANVAS_WIDTH, CANVAS_HEIGHT)

    # 1. ArUco pose recovery
    pose = detect_pose(captured, layout)
    if not pose.success:
        return _empty(f"ArUco pose failed: {pose.error}", pose_ok=False)

    # 2. Rectify
    rectified = rectify(captured, pose.homography, CANVAS_WIDTH, CANVAS_HEIGHT)

    # 3. Pilot fit — pillar 3: 16 distributed pilots, fit per-quadrant
    pilot_positions = np.array(
        [grid_index_to_pixel(i) for i in PILOT_INDICES], dtype=np.int64,
    )
    anchor_codeword_indices, anchor_patches_true = select_anchor_codewords(
        codebook, basis, params.amp, params.baseline, n_anchors=N_PILOTS,
    )
    anchor_pixel_positions = [(int(p[0]), int(p[1])) for p in pilot_positions]

    n_pilots_per_quadrant = [0, 0, 0, 0]
    cx_mid, cy_mid = CANVAS_WIDTH // 2, CANVAS_HEIGHT // 2
    for px, py in anchor_pixel_positions:
        qi = (1 if px >= cx_mid else 0) + (2 if py >= cy_mid else 0)
        n_pilots_per_quadrant[qi] += 1

    if use_per_quadrant_calibration:
        try:
            local_grid = fit_local_intensity_transforms(
                rectified, anchor_pixel_positions, anchor_patches_true,
                params.half_size, CANVAS_WIDTH, CANVAS_HEIGHT,
                n_x=2, n_y=2,
            )
            rectified_corrected = local_grid.invert(rectified).astype(np.float32)
            calibration_label = 'per-quadrant'
        except Exception as e:
            return _empty(f"local pilot fit failed: {e}", pose_ok=True)
    else:
        try:
            I_true_flat, I_observed_flat = gather_anchor_pixels(
                rectified, anchor_pixel_positions, anchor_patches_true, params.half_size,
            )
            transform = fit_intensity_transform(I_true_flat, I_observed_flat)
            rectified_corrected = transform.invert(rectified).astype(np.float32)
            calibration_label = 'global'
        except Exception as e:
            return _empty(f"global pilot fit failed: {e}", pose_ok=True)

    # 4. Manifest decode via image-space NCC
    manifest_nccs = []
    manifest_bytes = bytearray(MANIFEST_GERM_COUNT)
    for g, idx in enumerate(MANIFEST_INDICES):
        cx, cy = grid_index_to_pixel(idx)
        patch = _extract_patch(rectified_corrected, cx, cy, params.half_size)
        best_idx, best_ncc, _ = classify_patch(patch, templates)
        manifest_bytes[g] = best_idx
        manifest_nccs.append(best_ncc)
    median_manifest_ncc = float(np.median(manifest_nccs))

    try:
        n_payload_germs = parse_manifest_bytes(bytes(manifest_bytes))
    except Exception as e:
        return DecodeResult(
            filename='', payload=b'', sha256=b'',
            sha256_ok=False, size_ok=False, n_payload_germs=0,
            pose_ok=True, pilot_calibration=calibration_label,
            n_pilots_per_quadrant=n_pilots_per_quadrant,
            decode_error=f"manifest parse failed: {e}",
            median_manifest_ncc=median_manifest_ncc, median_payload_ncc=0.0,
            rs_corrected_frames=0, rs_failed_frames=[],
        )

    # 5. Payload decode via image-space NCC
    if n_payload_germs > PAYLOAD_CAPACITY:
        return _empty(
            f"manifest claims {n_payload_germs} germs, only {PAYLOAD_CAPACITY} available",
            pose_ok=True,
        )

    payload_indices = PAYLOAD_INDICES[:n_payload_germs]
    payload_bytes = bytearray(n_payload_germs)
    payload_nccs = []
    for g, idx in enumerate(payload_indices):
        cx, cy = grid_index_to_pixel(idx)
        patch = _extract_patch(rectified_corrected, cx, cy, params.half_size)
        best_idx, best_ncc, _ = classify_patch(patch, templates)
        payload_bytes[g] = best_idx
        payload_nccs.append(best_ncc)
    median_payload_ncc = float(np.median(payload_nccs))

    # 6. RS + AXP6 + Brotli + SHA-256
    try:
        framed, rs_stats = rs_decode(bytes(payload_bytes))
        parsed = parse_header(framed)
        decompressed = brotli.decompress(parsed['compressed_payload'])
    except Exception as e:
        return DecodeResult(
            filename='', payload=b'', sha256=b'',
            sha256_ok=False, size_ok=False, n_payload_germs=n_payload_germs,
            pose_ok=True, pilot_calibration=calibration_label,
            n_pilots_per_quadrant=n_pilots_per_quadrant,
            decode_error=f"final decode failed: {e}",
            median_manifest_ncc=median_manifest_ncc,
            median_payload_ncc=median_payload_ncc,
            rs_corrected_frames=0, rs_failed_frames=[],
        )

    actual_hash = hashlib.sha256(decompressed).digest()
    sha256_ok = actual_hash == parsed['expected_hash']
    size_ok = len(decompressed) == parsed['original_size']

    return DecodeResult(
        filename=parsed['filename'],
        payload=decompressed,
        sha256=actual_hash,
        sha256_ok=sha256_ok,
        size_ok=size_ok,
        n_payload_germs=n_payload_germs,
        pose_ok=True,
        pilot_calibration=calibration_label,
        n_pilots_per_quadrant=n_pilots_per_quadrant,
        decode_error=None,
        median_manifest_ncc=median_manifest_ncc,
        median_payload_ncc=median_payload_ncc,
        rs_corrected_frames=rs_stats['n_corrected'],
        rs_failed_frames=rs_stats['failed_frames'],
    )
