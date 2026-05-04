"""Spike-6 decoder: codebook modulation (nearest-neighbor in c_ortho).

Inverse of spike-6 encoder.
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
    nn_margin_min: float
    nn_margin_mean: float

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
            'nn_margin_min': self.nn_margin_min,
            'nn_margin_mean': self.nn_margin_mean,
        }


def _read_carrier(png_path: Path) -> np.ndarray:
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
    png_path = Path(png_path)
    manifest = json.loads(Path(manifest_path).read_text())

    params = EncodeParams(**manifest['params'])
    positions = np.array(manifest['positions'], dtype=np.int64)
    n_germs = manifest['n_germs']
    if positions.shape[0] != n_germs:
        raise ValueError(
            f"manifest position count ({positions.shape[0]}) != n_germs ({n_germs})"
        )

    carrier = _read_carrier(png_path)
    basis = OrthoBasis.build(params.half_size, params.sigma)
    codebook = design_codebook(
        basis, n_codewords=params.n_codewords, seed=params.codebook_seed,
    )

    # Linear LSQ inverse fit per germ position (spike-3 substrate, unchanged)
    thetas_raw, residuals = fit_carrier_sigmoid(
        carrier, positions, basis,
        amp=params.amp, baseline=params.baseline,
    )

    # Convert each fit to c_ortho, then nearest-neighbor decode against codebook
    decoded_bytes = bytearray(n_germs)
    margins = np.zeros(n_germs, dtype=np.float64)
    for g in range(n_germs):
        c_ortho = basis.M_to_ortho @ thetas_raw[g]
        b, _, margin = decode_with_confidence(c_ortho, codebook)
        decoded_bytes[g] = b
        margins[g] = margin

    rs_encoded = bytes(decoded_bytes)
    framed, rs_stats = rs_decode(rs_encoded)
    parsed = parse_header(framed)
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
        rs_corrected_frames=rs_stats['n_corrected'],
        rs_corrected_bytes=rs_stats['corrected_bytes'],
        rs_failed_frames=rs_stats['failed_frames'],
        extract_residual_max=float(np.max(residuals)) if len(residuals) else 0.0,
        extract_residual_mean=float(np.mean(residuals)) if len(residuals) else 0.0,
        nn_margin_min=float(margins.min()),
        nn_margin_mean=float(margins.mean()),
    )


def decode(png_path: Path, sidecar_path: Path | None = None) -> DecodeResult:
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
