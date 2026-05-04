"""Spike-5 encoder: spike-3 substrate + R-fold replication + RS(255, 191).

Pipeline:
    payload bytes
        -> Brotli q=11 compress
        -> AXP6 inner header
        -> Reed-Solomon RS(255, 191)                    [stronger ECC than spike-3]
        -> R-fold replication (default R=3)             [NEW: per-byte redundancy]
        -> pad to 5-byte germ boundary
        -> dequantize each 5-byte germ to c_ortho
        -> convert to theta_raw via M_to_raw
        -> place at known grid positions
        -> render via spike-3 sigmoid display
        -> save grayscale PNG (8-bit by default)
"""
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
import json

import brotli
import numpy as np
from PIL import Image

from header import pack_header
from germ_codec import (
    bytes_to_c_ortho, pad_bytes_to_germ_boundary,
)
from basis import OrthoBasis
from density import render_carrier_sigmoid, make_grid_positions
from ecc import rs_encode
from redundancy import replicate


@dataclass
class EncodeParams:
    sigma: float = 4.0
    half_size: int = 12
    spacing: int = 28
    margin: int = 24
    pixel_bit_depth: int = 8
    amp: float = 0.30
    baseline: float = 0.0
    background: float = 0.5
    R: int = 3                    # NEW: per-byte replication factor

    def to_dict(self) -> dict:
        return {
            'sigma': self.sigma, 'half_size': self.half_size,
            'spacing': self.spacing, 'margin': self.margin,
            'pixel_bit_depth': self.pixel_bit_depth,
            'amp': self.amp, 'baseline': self.baseline,
            'background': self.background,
            'R': self.R,
        }


def encode(
    payload: bytes,
    filename: str,
    out_path: Path,
    params: EncodeParams | None = None,
    sidecar: bool = True,
) -> dict:
    if params is None:
        params = EncodeParams()
    out_path = Path(out_path)

    compressed = brotli.compress(payload, quality=11)
    framed = pack_header(payload, compressed, filename)
    rs_encoded = rs_encode(framed)                              # RS(255, 191)
    replicated = replicate(rs_encoded, params.R)                # R-fold

    padded = pad_bytes_to_germ_boundary(replicated)
    n_germs = len(padded) // 5

    basis = OrthoBasis.build(params.half_size, params.sigma)
    c_orthos = np.zeros((n_germs, 5), dtype=np.float64)
    for g in range(n_germs):
        c_orthos[g] = bytes_to_c_ortho(padded[5 * g: 5 * (g + 1)], basis.codebook_bounds)
    thetas_raw = c_orthos @ basis.M_to_raw.T

    positions, width, height = make_grid_positions(
        n_germs, spacing=params.spacing, margin=params.margin,
    )
    canvas = render_carrier_sigmoid(
        thetas_raw, positions,
        width=width, height=height, basis=basis,
        amp=params.amp, baseline=params.baseline,
        background=params.background,
    )
    canvas = np.clip(canvas, 0.0, 1.0)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    if params.pixel_bit_depth == 8:
        img = (canvas * 255.0 + 0.5).astype(np.uint8)
        Image.fromarray(img, mode='L').save(out_path, format='PNG')
    elif params.pixel_bit_depth == 16:
        img = (canvas * 65535.0 + 0.5).astype(np.uint16)
        Image.fromarray(img, mode='I;16').save(out_path, format='PNG')
    else:
        raise ValueError(f"unsupported pixel_bit_depth {params.pixel_bit_depth}")

    manifest = {
        'spike_version': '5.0',
        'filename': filename,
        'payload_size': len(payload),
        'compressed_size': len(compressed),
        'framed_size': len(framed),
        'rs_encoded_size': len(rs_encoded),
        'replicated_size': len(replicated),
        'padded_size': len(padded),
        'n_germs': n_germs,
        'width': width,
        'height': height,
        'params': params.to_dict(),
        'positions': positions.tolist(),
    }
    if sidecar:
        sidecar_path = out_path.with_suffix(out_path.suffix + '.manifest.json')
        sidecar_path.write_text(json.dumps(manifest, indent=2))
        manifest['sidecar_path'] = str(sidecar_path)
    manifest['png_path'] = str(out_path)
    manifest['png_bytes'] = out_path.stat().st_size
    return manifest


if __name__ == '__main__':
    import sys
    if len(sys.argv) < 3:
        print("usage: python encoder.py <input> <output.png> [bit_depth]")
        sys.exit(1)
    in_path = Path(sys.argv[1])
    out_path = Path(sys.argv[2])
    depth = int(sys.argv[3]) if len(sys.argv) >= 4 else 8
    payload = in_path.read_bytes()
    mf = encode(payload, in_path.name, out_path,
                params=EncodeParams(pixel_bit_depth=depth))
    print(json.dumps({k: v for k, v in mf.items() if k != 'positions'}, indent=2))
