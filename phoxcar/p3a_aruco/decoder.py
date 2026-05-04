"""P3.A decoder: ArUco fiducial pose recovery + spike-7 pipeline.

NO SIDECAR. Decoder uses only:
  - format spec constants (canvas size, grid layout, codebook seed)
  - in-carrier manifest cluster
  - in-carrier ArUco markers (this is the layer-5 substrate)

Pipeline:
    PNG carrier (potentially warped, noisy, off-axis)
      -> read 8-bit grayscale
      -> cv2.aruco.detectMarkers
      -> identify NW/NE/SW/SE markers (IDs 0/1/2/3) by ID, not geometry
      -> 4-point homography (observed -> canonical 1280x1280)
      -> rectify
      -> sample manifest at canonical positions -> RS-byte-count
      -> sample pilots at canonical positions -> intensity transform fit
      -> apply inverse transform to rectified image
      -> sample payload at canonical positions -> codebook NN
      -> RS + AXP6 + Brotli + SHA-256 verify
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
    pose_ok: bool
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
            'pose_ok': self.pose_ok,
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


def _empty(error: str, pose_ok: bool = False) -> DecodeResult:
    return DecodeResult(
        filename='', payload=b'', sha256=b'',
        sha256_ok=False, size_ok=False, n_payload_germs=0, transform=None,
        rs_corrected_frames=0, rs_failed_frames=[],
        pose_ok=pose_ok, decode_error=error,
    )


def decode(png_path: Path, params: EncodeParams | None = None) -> DecodeResult:
    if params is None:
        params = EncodeParams()
    png_path = Path(png_path)
    captured = _read_image(png_path)

    basis = OrthoBasis.build(params.half_size, params.sigma)
    codebook = design_codebook(
        basis, n_codewords=params.n_codewords, seed=params.codebook_seed,
    )
    layout = canonical_layout(CANVAS_WIDTH, CANVAS_HEIGHT)

    # 1. ArUco pose recovery
    pose = detect_pose(captured, layout)
    if not pose.success:
        return _empty(f"ArUco pose failed: {pose.error}", pose_ok=False)

    # 2. Rectify to canonical frame
    rectified = rectify(captured, pose.homography, CANVAS_WIDTH, CANVAS_HEIGHT)

    # 3. Pilot fit FIRST (before manifest read) so the intensity transform
    #    can correct the rectified image before any codebook NN decode runs.
    #    This avoids the chicken-and-egg between the manifest cluster and
    #    the calibration pilots.
    pilot_positions = np.array(
        [grid_index_to_pixel(i) for i in PILOT_INDICES], dtype=np.int64,
    )
    anchor_codeword_indices, anchor_patches_true = select_anchor_codewords(
        codebook, basis, params.amp, params.baseline, n_anchors=N_PILOTS,
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

    # 4. Sample manifest at canonical positions (on the corrected image).
    manifest_positions = np.array(
        [grid_index_to_pixel(i) for i in MANIFEST_INDICES], dtype=np.int64,
    )
    try:
        manifest_thetas, _ = fit_carrier_sigmoid(
            rectified_corrected, manifest_positions, basis,
            amp=params.amp, baseline=params.baseline,
        )
    except Exception as e:
        return _empty(f"manifest fit failed: {e}", pose_ok=True)
    manifest_bytes = bytearray(MANIFEST_GERM_COUNT)
    for g in range(MANIFEST_GERM_COUNT):
        c_ortho = basis.M_to_ortho @ manifest_thetas[g]
        b, _, _ = decode_with_confidence(c_ortho, codebook)
        manifest_bytes[g] = b
    try:
        n_payload_germs = parse_manifest_bytes(bytes(manifest_bytes))
    except Exception as e:
        return _empty(f"manifest parse failed: {e}", pose_ok=True)

    # 5. Payload decode
    if PAYLOAD_START_INDEX + n_payload_germs > GRID_SLOTS:
        return _empty(
            f"manifest claims {n_payload_germs} payload germs but grid only "
            f"has {GRID_SLOTS - PAYLOAD_START_INDEX} slots after manifest+pilots",
            pose_ok=True,
        )
    payload_indices = list(range(PAYLOAD_START_INDEX,
                                   PAYLOAD_START_INDEX + n_payload_germs))
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

    # 6. RS + AXP6 + Brotli + SHA-256
    try:
        framed, rs_stats = rs_decode(bytes(payload_bytes))
        parsed = parse_header(framed)
        decompressed = brotli.decompress(parsed['compressed_payload'])
    except Exception as e:
        return _empty(f"final decode failed: {e}", pose_ok=True)

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
        pose_ok=True,
        decode_error=None,
    )


if __name__ == '__main__':
    import sys
    if len(sys.argv) < 2:
        print("usage: python decoder.py <carrier.png>")
        sys.exit(1)
    png = Path(sys.argv[1])
    res = decode(png)
    if res.sha256_ok:
        print(json.dumps(res.summary(), indent=2))
    else:
        print(json.dumps(res.summary(), indent=2))
