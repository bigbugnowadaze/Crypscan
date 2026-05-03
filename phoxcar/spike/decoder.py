"""End-to-end phoxcar spike DECODER.

Pipeline (inverse of encoder):
    PNG carrier
        -> read 8-bit grayscale
        -> at each known position, fit 5-coef germ via linear LSQ
           (extract.extract_carrier)
        -> germs -> bytes (germ_codec.germs_to_bytes)
        -> parse AXP6-equivalent inner header (header.parse_header)
        -> Brotli decompress
        -> SHA-256 verify against the hash stored in the inner header
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
from germ_codec import germs_to_bytes
from extract import extract_carrier
from encoder import EncodeParams


@dataclass
class DecodeResult:
    filename: str
    payload: bytes
    sha256: bytes
    sha256_ok: bool
    size_ok: bool
    n_germs: int
    per_coef_rmse: np.ndarray            # (5,) RMSE between recovered and quantized germs
    extract_residual_max: float
    extract_residual_mean: float

    def summary(self) -> dict:
        return {
            'filename': self.filename,
            'sha256': self.sha256.hex(),
            'sha256_ok': self.sha256_ok,
            'size_ok': self.size_ok,
            'n_germs': self.n_germs,
            'per_coef_rmse': self.per_coef_rmse.tolist(),
            'extract_residual_max': self.extract_residual_max,
            'extract_residual_mean': self.extract_residual_mean,
        }


def decode_with_manifest(
    png_path: Path,
    manifest_path: Path,
) -> DecodeResult:
    """Decode using the sidecar manifest from the encoder.

    Phase 1 will encode the manifest as a known-position germ cluster in the
    carrier itself (`03_PHOXOIDAL_CARRIER_ARCHITECTURE.md` section 7); the
    spike reads it from a JSON sidecar.
    """
    png_path = Path(png_path)
    manifest = json.loads(Path(manifest_path).read_text())

    params = EncodeParams(**manifest['params'])
    positions = np.array(manifest['positions'], dtype=np.int64)
    n_germs = manifest['n_germs']
    if positions.shape[0] != n_germs:
        raise ValueError(
            f"manifest position count ({positions.shape[0]}) != n_germs ({n_germs})"
        )

    # Read the PNG and normalize to [0, 1]. PIL gives mode='L' (8-bit) or
    # mode='I;16' (16-bit) for grayscale PNGs.
    img = Image.open(png_path)
    arr = np.asarray(img)
    if img.mode == 'L':
        carrier = arr.astype(np.float32) / 255.0
    elif img.mode == 'I;16':
        carrier = arr.astype(np.float32) / 65535.0
    elif img.mode == 'I':
        # Some PIL versions decode 16-bit as mode='I' (32-bit signed)
        carrier = arr.astype(np.float32) / 65535.0
    else:
        # Fall back: convert to L and treat as 8-bit
        carrier = np.asarray(img.convert('L'), dtype=np.float32) / 255.0

    # Run inverse fit at each known position.
    germs, residuals = extract_carrier(
        carrier, positions,
        sigma=params.sigma, half_size=params.half_size,
        amp=params.amp, baseline=params.baseline,
    )

    # Compute per-coefficient RMSE against the encoder's quantized germs.
    # We don't have the encoder's germs at decode time normally, but since
    # the manifest has the original payload-size we can re-derive them by
    # reading the encoder-side reference if present (results/ directory in
    # the spike's test). For now we just compute the magnitude of the
    # recovered coefficients for monitoring.
    # (Per-coef RMSE vs encoder will be filled in by test_roundtrip.)
    per_coef_rmse = np.full(5, np.nan)

    # Germs -> bytes (the dequantization grid round-trips by construction).
    payload_bytes = germs_to_bytes(germs)

    # Parse AXP6 inner header.
    parsed = parse_header(payload_bytes)
    decompressed = brotli.decompress(parsed['compressed_payload'])

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
        per_coef_rmse=per_coef_rmse,
        extract_residual_max=float(np.max(residuals)) if len(residuals) else 0.0,
        extract_residual_mean=float(np.mean(residuals)) if len(residuals) else 0.0,
    )


def decode(png_path: Path, sidecar_path: Path | None = None) -> DecodeResult:
    """Decode a phoxcar PNG. The sidecar manifest is required (Phase 0.5)."""
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
