"""Spike-8A decoder: pose recovery + rectification + spike-7 pipeline.

NO JSON SIDECAR USED. The decoder relies only on:
    1. Format spec constants (canvas size, finder positions, grid layout,
       codebook seed, sigma/half_size/amp/baseline)
    2. The in-carrier manifest cluster (which encodes the RS-encoded
       payload byte count)

Pipeline:
    PNG carrier (potentially warped, noisy, off-axis)
      -> read 8-bit grayscale
      -> detect 4 finder corners (pose.detect_finders)
      -> compute homography to canonical 1280x1280 frame
      -> rectify
      -> at canonical manifest positions, sample 8 germs -> NN decode -> bytes
         -> parse manifest (PHX1 magic + RS-encoded byte count)
      -> at canonical pilot positions, fit intensity transform
      -> apply inverse transform to entire rectified image
      -> at canonical payload positions (derived from manifest), sample germs
         -> NN decode -> bytes
      -> RS decode + AXP6 + Brotli + SHA-256 verify
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
from solver import fit_carrier_sigmoid
from ecc import rs_decode
from codebook import design_codebook, decode_with_confidence
from density import render_germ_patch_sigmoid
from pilots import (
    fit_intensity_transform, gather_anchor_pixels, IntensityTransform,
)
from finders import (
    FINDER_GLYPH_A, FINDER_GLYPH_B, FINDER_AMP, FINDER_MARGIN,
    canonical_finder_positions, render_finder_patch,
)
from manifest import (
    parse_manifest_bytes, MANIFEST_BYTE_COUNT, MANIFEST_GERM_COUNT,
)
from pose import detect_finders, estimate_homography, rectify_carrier
from encoder import (
    CANVAS_WIDTH, CANVAS_HEIGHT, GRID_COLS, GRID_ROWS, GRID_SLOTS,
    SPACING, GRID_ORIGIN_X, GRID_ORIGIN_Y, INNER_MARGIN,
    MANIFEST_INDICES, PILOT_INDICES, PAYLOAD_START_INDEX,
    EncodeParams, grid_index_to_pixel, N_PILOTS,
)


@dataclass
class DecodeResult:
    filename: str
    payload: bytes
    sha256: bytes
    sha256_ok: bool
    size_ok: bool
    n_payload_germs: int
    transform: IntensityTransform | None
    rs_corrected_frames: int
    rs_failed_frames: list
    finder_detection_ok: bool
    decode_error: str | None

    def summary(self) -> dict:
        return {
            'filename': self.filename,
            'sha256': self.sha256.hex() if self.sha256 else None,
            'sha256_ok': bool(self.sha256_ok),
            'size_ok': bool(self.size_ok),
            'n_payload_germs': self.n_payload_germs,
            'transform': self.transform.to_dict() if self.transform else None,
            'rs_corrected_frames': self.rs_corrected_frames,
            'rs_failed_frames': self.rs_failed_frames,
            'finder_detection_ok': self.finder_detection_ok,
            'decode_error': self.decode_error,
        }


def _read_image(png_path: Path) -> np.ndarray:
    img = Image.open(png_path)
    arr = np.asarray(img)
    if img.mode == 'L':
        return arr.astype(np.float32) / 255.0
    if img.mode in ('I;16', 'I'):
        return arr.astype(np.float32) / 65535.0
    return np.asarray(img.convert('L'), dtype=np.float32) / 255.0


def _empty_result(error: str, finder_ok: bool = False) -> DecodeResult:
    return DecodeResult(
        filename='', payload=b'', sha256=b'',
        sha256_ok=False, size_ok=False,
        n_payload_germs=0, transform=None,
        rs_corrected_frames=0, rs_failed_frames=[],
        finder_detection_ok=finder_ok, decode_error=error,
    )


def decode(png_path: Path, params: EncodeParams | None = None) -> DecodeResult:
    """Decode a phoxcar carrier WITHOUT sidecar."""
    if params is None:
        params = EncodeParams()
    png_path = Path(png_path)
    captured = _read_image(png_path)

    basis = OrthoBasis.build(params.half_size, params.sigma)
    codebook = design_codebook(
        basis, n_codewords=params.n_codewords, seed=params.codebook_seed,
    )

    # 1. Detect 4 corner finders in the captured image
    observed_corners = detect_finders(
        captured, basis,
        codebook_seed=params.codebook_seed,
        n_codewords=params.n_codewords,
    )
    if observed_corners is None:
        return _empty_result("could not detect 4 finder corners", finder_ok=False)

    canonical_corners = canonical_finder_positions(
        CANVAS_WIDTH, CANVAS_HEIGHT, FINDER_MARGIN,
    )

    # 2. Estimate homography (observed -> canonical)
    homography = estimate_homography(observed_corners, canonical_corners)
    if homography is None:
        return _empty_result("homography estimation failed", finder_ok=True)

    # 3. Rectify the captured image to canonical 1280x1280 coordinates
    rectified = rectify_carrier(captured, CANVAS_WIDTH, CANVAS_HEIGHT, homography)

    # 4. Sample manifest germs at canonical positions, decode via codebook NN
    manifest_positions = np.array(
        [grid_index_to_pixel(i) for i in MANIFEST_INDICES], dtype=np.int64,
    )
    try:
        manifest_thetas, _ = fit_carrier_sigmoid(
            rectified, manifest_positions, basis,
            amp=params.amp, baseline=params.baseline,
        )
    except Exception as e:
        return _empty_result(f"manifest fit failed: {e}", finder_ok=True)
    manifest_bytes = bytearray(MANIFEST_GERM_COUNT)
    for g in range(MANIFEST_GERM_COUNT):
        c_ortho = basis.M_to_ortho @ manifest_thetas[g]
        b, _, _ = decode_with_confidence(c_ortho, codebook)
        manifest_bytes[g] = b
    try:
        n_payload_germs = parse_manifest_bytes(bytes(manifest_bytes))
    except Exception as e:
        return _empty_result(f"manifest parse failed: {e}", finder_ok=True)

    # 5. Sample pilot germs, fit intensity transform (spike-7 logic)
    pilot_positions = np.array(
        [grid_index_to_pixel(i) for i in PILOT_INDICES], dtype=np.int64,
    )
    # Re-derive expected pilot patches from anchor codewords (selected
    # deterministically from the codebook + amp/baseline)
    from pilots import select_anchor_codewords
    anchor_codeword_indices, anchor_patches_true = select_anchor_codewords(
        codebook, basis, params.amp, params.baseline, n_anchors=N_PILOTS,
    )
    # Anchor positions correspond directly to PILOT_INDICES grid slots
    anchor_pixel_positions = [
        (int(p[0]), int(p[1])) for p in pilot_positions
    ]
    try:
        I_true_flat, I_observed_flat = gather_anchor_pixels(
            rectified, anchor_pixel_positions, anchor_patches_true, params.half_size,
        )
        transform = fit_intensity_transform(I_true_flat, I_observed_flat)
    except Exception as e:
        return _empty_result(f"pilot fit failed: {e}", finder_ok=True)

    rectified_corrected = transform.invert(rectified).astype(np.float32)

    # 6. Sample payload germs at canonical positions, decode via codebook NN
    payload_indices = list(range(PAYLOAD_START_INDEX,
                                   PAYLOAD_START_INDEX + n_payload_germs))
    if PAYLOAD_START_INDEX + n_payload_germs > GRID_SLOTS:
        return _empty_result(
            f"manifest claims {n_payload_germs} payload germs but grid only "
            f"has {GRID_SLOTS - PAYLOAD_START_INDEX} slots after manifest+pilots",
            finder_ok=True,
        )
    payload_positions = np.array(
        [grid_index_to_pixel(i) for i in payload_indices], dtype=np.int64,
    )
    payload_thetas, _ = fit_carrier_sigmoid(
        rectified_corrected, payload_positions, basis,
        amp=params.amp, baseline=params.baseline,
    )
    payload_bytes = bytearray(n_payload_germs)
    for g in range(n_payload_germs):
        c_ortho = basis.M_to_ortho @ payload_thetas[g]
        b, _, _ = decode_with_confidence(c_ortho, codebook)
        payload_bytes[g] = b

    # 7. RS decode + AXP6 + Brotli + SHA-256
    try:
        framed, rs_stats = rs_decode(bytes(payload_bytes))
        parsed = parse_header(framed)
        decompressed = brotli.decompress(parsed['compressed_payload'])
    except Exception as e:
        return _empty_result(f"final decode failed: {e}", finder_ok=True)

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
        transform=transform,
        rs_corrected_frames=rs_stats['n_corrected'],
        rs_failed_frames=rs_stats['failed_frames'],
        finder_detection_ok=True,
        decode_error=None,
    )


if __name__ == '__main__':
    import sys
    if len(sys.argv) < 2:
        print("usage: python decoder.py <carrier.png>")
        sys.exit(1)
    png = Path(sys.argv[1])
    out_dir = Path(sys.argv[2]) if len(sys.argv) >= 3 else png.parent
    res = decode(png)
    if res.sha256_ok:
        out_path = out_dir / res.filename
        out_path.write_bytes(res.payload)
        print(json.dumps({**res.summary(), 'output': str(out_path)}, indent=2))
    else:
        print(json.dumps(res.summary(), indent=2))
