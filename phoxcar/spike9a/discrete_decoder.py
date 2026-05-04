"""P3.A-compatible decoder using image-space NCC classifier instead of
coefficient-space LSQ + NN.

Per ADDENDUM_04 §3 #1: replace the catastrophe-germ 5-coefficient LSQ fit
with direct NCC classification of the patch against pre-rendered codeword
templates.

Pipeline:
    PNG -> read 8-bit grayscale -> ArUco pose (unchanged) -> rectify
    -> pilots fit + inverse correction (unchanged)
    -> for each germ position:
        extract 25x25 patch from rectified-corrected image
        NCC against N pre-rendered templates
        pick best match -> codeword index -> byte
    -> RS + AXP6 + Brotli + SHA-256 (unchanged)

The decoder configurable: N=256 (full codebook, image-space NCC) or
N=16 (subset, image-space NCC). Both bypass the 5-coefficient solver.
"""
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
import hashlib

import brotli
import numpy as np
from PIL import Image

from header import parse_header
from basis import OrthoBasis
from ecc import rs_decode
from codebook import design_codebook
from pilots import (
    fit_intensity_transform, gather_anchor_pixels, IntensityTransform,
    select_anchor_codewords,
)
from manifest import parse_manifest_bytes, MANIFEST_GERM_COUNT
from fiducials import canonical_layout
from pose import detect_pose, rectify
from encoder import (
    CANVAS_WIDTH, CANVAS_HEIGHT, GRID_SLOTS,
    MANIFEST_INDICES, PILOT_INDICES, PAYLOAD_START_INDEX,
    EncodeParams, grid_index_to_pixel, N_PILOTS,
)
from discrete_codebook import (
    render_codebook_patches, classify_patch, select_discrete_subset,
)


@dataclass
class DiscreteDecodeResult:
    filename: str
    payload: bytes
    sha256: bytes
    sha256_ok: bool
    size_ok: bool
    n_payload_germs: int
    transform: IntensityTransform | None
    rs_corrected_frames: int
    rs_failed_frames: list
    pose_ok: bool
    decode_error: str | None
    # Per-germ classification confidence stats
    median_manifest_ncc: float
    median_payload_ncc: float


def _read_image(png_path: Path) -> np.ndarray:
    img = Image.open(png_path)
    arr = np.asarray(img)
    if img.mode == 'L':
        return arr.astype(np.float32) / 255.0
    if img.mode in ('I;16', 'I'):
        return arr.astype(np.float32) / 65535.0
    return np.asarray(img.convert('L'), dtype=np.float32) / 255.0


def _empty(error: str, pose_ok: bool = False) -> DiscreteDecodeResult:
    return DiscreteDecodeResult(
        filename='', payload=b'', sha256=b'',
        sha256_ok=False, size_ok=False, n_payload_germs=0, transform=None,
        rs_corrected_frames=0, rs_failed_frames=[],
        pose_ok=pose_ok, decode_error=error,
        median_manifest_ncc=0.0, median_payload_ncc=0.0,
    )


def _extract_patch(image: np.ndarray, cx: int, cy: int, half_size: int) -> np.ndarray:
    """Extract a (side, side) patch centered at (cx, cy) from image."""
    side = 2 * half_size + 1
    x0 = cx - half_size; x1 = cx + half_size + 1
    y0 = cy - half_size; y1 = cy + half_size + 1
    if x0 < 0 or y0 < 0 or x1 > image.shape[1] or y1 > image.shape[0]:
        return np.full((side, side), 0.5, dtype=np.float32)
    return image[y0:y1, x0:x1].astype(np.float32)


def decode_discrete(png_path: Path,
                      n_codewords: int = 16,
                      params: EncodeParams | None = None,
                      ) -> DiscreteDecodeResult:
    """Decode a P3.A-format carrier using image-space NCC against an
    N-codeword discrete subset.

    The encoder is unchanged; the same 256-codeword codebook is used to
    encode bytes (mod n_codewords if n_codewords < 256). The decoder
    pre-renders the codebook (or a discrete subset of it) and classifies
    each germ patch by NCC.

    Args:
        png_path: PNG carrier path.
        n_codewords: how many codewords to use. 256 = full codebook
            image-space NCC; 16 = 4-bit subset; 4 = 2-bit subset; etc.
        params: optional EncodeParams (must match encoder).

    NOTE: this decoder ASSUMES the encoder used the matched discrete
    subset (i.e. encoded byte b -> codebook[discrete_indices[b mod n]]).
    For now, we test using n_codewords=256 (full set, just changing the
    decode metric) AND with discrete encoding via discrete_encoder.py.
    """
    if params is None:
        params = EncodeParams()
    png_path = Path(png_path)
    captured = _read_image(png_path)

    basis = OrthoBasis.build(params.half_size, params.sigma)
    full_codebook = design_codebook(
        basis, n_codewords=params.n_codewords, seed=params.codebook_seed,
    )
    if n_codewords < params.n_codewords:
        subset, subset_indices = select_discrete_subset(
            full_codebook, basis, n_keep=n_codewords, amp=params.amp,
            baseline=params.baseline, seed=params.codebook_seed,
        )
        active_codebook = subset
    else:
        active_codebook = full_codebook
        subset_indices = np.arange(n_codewords)

    templates = render_codebook_patches(active_codebook, basis,
                                          amp=params.amp,
                                          baseline=params.baseline)

    layout = canonical_layout(CANVAS_WIDTH, CANVAS_HEIGHT)

    # 1. ArUco pose recovery
    pose = detect_pose(captured, layout)
    if not pose.success:
        return _empty(f"ArUco pose failed: {pose.error}", pose_ok=False)

    # 2. Rectify
    rectified = rectify(captured, pose.homography, CANVAS_WIDTH, CANVAS_HEIGHT)

    # 3. Pilot fit (uses original full codebook anchor selection because
    #    encoder used full codebook for pilots — this is a constraint
    #    we work within for spike-9A)
    pilot_positions = np.array(
        [grid_index_to_pixel(i) for i in PILOT_INDICES], dtype=np.int64,
    )
    anchor_codeword_indices, anchor_patches_true = select_anchor_codewords(
        full_codebook, basis, params.amp, params.baseline, n_anchors=N_PILOTS,
    )
    anchor_pixel_positions = [(int(p[0]), int(p[1])) for p in pilot_positions]
    try:
        I_true_flat, I_observed_flat = gather_anchor_pixels(
            rectified, anchor_pixel_positions, anchor_patches_true, params.half_size,
        )
        transform = fit_intensity_transform(I_true_flat, I_observed_flat)
    except Exception as e:
        return _empty(f"pilot fit failed: {e}", pose_ok=True)

    rectified_corrected = transform.invert(rectified).astype(np.float32)

    # 4. Sample manifest cluster - image-space NCC classifier
    manifest_nccs = []
    manifest_bytes = bytearray(MANIFEST_GERM_COUNT)
    for g, idx in enumerate(MANIFEST_INDICES):
        cx, cy = grid_index_to_pixel(idx)
        patch = _extract_patch(rectified_corrected, cx, cy, params.half_size)
        best_idx, best_ncc, margin = classify_patch(patch, templates)
        # Map back to original codebook index space
        manifest_bytes[g] = int(subset_indices[best_idx]) % 256
        manifest_nccs.append(best_ncc)
    median_manifest_ncc = float(np.median(manifest_nccs))

    try:
        n_payload_germs = parse_manifest_bytes(bytes(manifest_bytes))
    except Exception as e:
        return DiscreteDecodeResult(
            filename='', payload=b'', sha256=b'',
            sha256_ok=False, size_ok=False, n_payload_germs=0, transform=transform,
            rs_corrected_frames=0, rs_failed_frames=[], pose_ok=True,
            decode_error=f"manifest parse failed: {e}",
            median_manifest_ncc=median_manifest_ncc, median_payload_ncc=0.0,
        )

    # 5. Payload decode
    if PAYLOAD_START_INDEX + n_payload_germs > GRID_SLOTS:
        return _empty(
            f"manifest claims {n_payload_germs} payload germs, only "
            f"{GRID_SLOTS - PAYLOAD_START_INDEX} available",
            pose_ok=True,
        )

    payload_indices = list(range(PAYLOAD_START_INDEX,
                                   PAYLOAD_START_INDEX + n_payload_germs))
    payload_bytes = bytearray(n_payload_germs)
    payload_nccs = []
    for g, idx in enumerate(payload_indices):
        cx, cy = grid_index_to_pixel(idx)
        patch = _extract_patch(rectified_corrected, cx, cy, params.half_size)
        best_idx, best_ncc, _ = classify_patch(patch, templates)
        payload_bytes[g] = int(subset_indices[best_idx]) % 256
        payload_nccs.append(best_ncc)
    median_payload_ncc = float(np.median(payload_nccs))

    # 6. RS + AXP6 + Brotli + SHA-256
    try:
        framed, rs_stats = rs_decode(bytes(payload_bytes))
        parsed = parse_header(framed)
        decompressed = brotli.decompress(parsed['compressed_payload'])
    except Exception as e:
        return DiscreteDecodeResult(
            filename='', payload=b'', sha256=b'',
            sha256_ok=False, size_ok=False, n_payload_germs=n_payload_germs,
            transform=transform, rs_corrected_frames=0, rs_failed_frames=[],
            pose_ok=True, decode_error=f"final decode failed: {e}",
            median_manifest_ncc=median_manifest_ncc,
            median_payload_ncc=median_payload_ncc,
        )

    actual_hash = hashlib.sha256(decompressed).digest()
    sha256_ok = actual_hash == parsed['expected_hash']
    size_ok = len(decompressed) == parsed['original_size']

    return DiscreteDecodeResult(
        filename=parsed['filename'],
        payload=decompressed,
        sha256=actual_hash,
        sha256_ok=sha256_ok,
        size_ok=size_ok,
        n_payload_germs=n_payload_germs,
        transform=transform,
        rs_corrected_frames=rs_stats['n_corrected'],
        rs_failed_frames=rs_stats['failed_frames'],
        pose_ok=True,
        decode_error=None,
        median_manifest_ncc=median_manifest_ncc,
        median_payload_ncc=median_payload_ncc,
    )
