"""End-to-end phoxcar spike-2 DECODER (CRYPSOID-faithful).

Pipeline (inverse of encoder):
    PNG carrier
        -> read grayscale (8 or 16 bit; auto-detect via PIL mode)
        -> at each known position, fit theta_raw via Levenberg-Marquardt
           on the strict log-space residual
        -> convert theta_raw -> c_ortho (5,) via M_to_ortho
        -> apply sign convention: if c_ortho[0] < 0, negate the whole vector
        -> quantize each canonical c_ortho to 5 bytes per germ
        -> bit-unpack the germ bytes into the RS-encoded byte stream
        -> RS decode (correct up to 16 byte flips per 255-byte frame)
        -> parse AXP6 inner header
        -> Brotli decompress
        -> SHA-256 verify
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
from germ_codec import (
    bit_unpack_germ_bytes_to_payload, c_ortho_to_bytes, canonicalize_sign,
)
from basis import OrthoBasis
from solver import fit_carrier_strict
from ecc import rs_decode
from encoder import EncodeParams


@dataclass
class DecodeResult:
    filename: str
    payload: bytes
    sha256: bytes
    sha256_ok: bool
    size_ok: bool
    n_germs: int
    rs_corrected_frames: int
    rs_corrected_bytes: int
    rs_failed_frames: list
    extract_residual_max: float
    extract_residual_mean: float
    sign_flips_applied: int

    def summary(self) -> dict:
        return {
            'filename': self.filename,
            'sha256': self.sha256.hex(),
            'sha256_ok': bool(self.sha256_ok),
            'size_ok': bool(self.size_ok),
            'n_germs': self.n_germs,
            'rs_corrected_frames': self.rs_corrected_frames,
            'rs_corrected_bytes': self.rs_corrected_bytes,
            'rs_failed_frames': self.rs_failed_frames,
            'extract_residual_max': self.extract_residual_max,
            'extract_residual_mean': self.extract_residual_mean,
            'sign_flips_applied': self.sign_flips_applied,
        }


def _read_carrier_image(png_path: Path) -> np.ndarray:
    """Load a grayscale PNG and normalize to [0, 1] float32."""
    img = Image.open(png_path)
    arr = np.asarray(img)
    if img.mode == 'L':
        return arr.astype(np.float32) / 255.0
    if img.mode in ('I;16', 'I'):
        return arr.astype(np.float32) / 65535.0
    return np.asarray(img.convert('L'), dtype=np.float32) / 255.0


def decode_with_manifest(
    png_path: Path,
    manifest_path: Path,
) -> DecodeResult:
    """Decode using the encoder's sidecar manifest (Phase 0.5 only)."""
    png_path = Path(png_path)
    manifest = json.loads(Path(manifest_path).read_text())

    params = EncodeParams(**manifest['params'])
    positions = np.array(manifest['positions'], dtype=np.int64)
    n_germs = manifest['n_germs']
    if positions.shape[0] != n_germs:
        raise ValueError(
            f"manifest position count ({positions.shape[0]}) != n_germs ({n_germs})"
        )

    carrier = _read_carrier_image(png_path)

    # 1. Build orthonormal basis (must match encoder's params)
    basis = OrthoBasis.build(params.half_size, params.sigma)

    # 2. Nonlinear fit at every known position
    thetas_raw, residuals = fit_carrier_strict(carrier, positions, basis)

    # 3. Convert to c_ortho, canonicalize sign, quantize back to bytes
    germ_bytes = bytearray()
    sign_flips = 0
    for g in range(n_germs):
        c_ortho = basis.M_to_ortho @ thetas_raw[g]
        c_canon, was_flipped = canonicalize_sign(c_ortho)
        if was_flipped:
            sign_flips += 1
        germ_bytes += c_ortho_to_bytes(c_canon, basis.codebook_bounds)

    # 4. Bit-unpack into the RS-encoded byte stream
    rs_encoded_size = manifest['rs_encoded_size']
    rs_encoded = bit_unpack_germ_bytes_to_payload(bytes(germ_bytes), rs_encoded_size)

    # 5. RS decode (up to 16 byte flips per 255-byte frame)
    framed, rs_stats = rs_decode(rs_encoded)

    # 6. Parse AXP6 inner header
    parsed = parse_header(framed)

    # 7. Brotli decompress
    decompressed = brotli.decompress(parsed['compressed_payload'])

    # 8. SHA-256 verify
    actual_hash = hashlib.sha256(decompressed).digest()
    sha256_ok = actual_hash == parsed['expected_hash']
    size_ok = len(decompressed) == parsed['original_size']

    return DecodeResult(
        filename=parsed['filename'],
        payload=decompressed,
        sha256=actual_hash,
        sha256_ok=sha256_ok,
        size_ok=size_ok,
        n_germs=n_germs,
        rs_corrected_frames=rs_stats['n_corrected'],
        rs_corrected_bytes=rs_stats['corrected_bytes'],
        rs_failed_frames=rs_stats['failed_frames'],
        extract_residual_max=float(np.max(residuals)) if len(residuals) else 0.0,
        extract_residual_mean=float(np.mean(residuals)) if len(residuals) else 0.0,
        sign_flips_applied=sign_flips,
    )


def decode(png_path: Path, sidecar_path: Path | None = None) -> DecodeResult:
    """Decode a phoxcar spike-2 PNG. The sidecar manifest is required."""
    png_path = Path(png_path)
    if sidecar_path is None:
        sidecar_path = png_path.with_suffix(png_path.suffix + '.manifest.json')
    return decode_with_manifest(png_path, sidecar_path)


if __name__ == '__main__':
    import sys
    if len(sys.argv) < 2:
        print("usage: python decoder.py <carrier.png>")
        sys.exit(1)
    png = Path(sys.argv[1])
    out_dir = Path(sys.argv[2]) if len(sys.argv) >= 3 else png.parent
    res = decode(png)
    out_path = out_dir / res.filename
    out_path.write_bytes(res.payload)
    print(json.dumps({**res.summary(), 'output': str(out_path)}, indent=2))
