"""Spike-6 encoder: codebook modulation (1 byte/germ via 256-glyph codebook).

Pipeline:
    payload bytes
        -> Brotli q=11 compress
        -> AXP6 inner header
        -> Reed-Solomon RS(255, 223)         (same as spike-3/4)
        -> map each byte -> codebook[byte] = c_ortho 5-vector
        -> c_ortho -> theta_raw via M_to_raw
        -> place at known scene positions on a grid
        -> render via spike-3 sigmoid display function
        -> save grayscale PNG

Density: 1 byte/germ vs spike-3's 5 bytes/germ. 5x more germs needed
for the same payload — the price for digital-symbol codebook robustness
under camera-channel noise.
"""
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
import json

import brotli
import numpy as np
from PIL import Image

from header import pack_header
from basis import OrthoBasis
from density import render_carrier_sigmoid, make_grid_positions
from ecc import rs_encode
from codebook import design_codebook


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
    n_codewords: int = 256
    codebook_seed: int = 20260504

    def to_dict(self) -> dict:
        return {
            'sigma': self.sigma, 'half_size': self.half_size,
            'spacing': self.spacing, 'margin': self.margin,
            'pixel_bit_depth': self.pixel_bit_depth,
            'amp': self.amp, 'baseline': self.baseline,
            'background': self.background,
            'n_codewords': self.n_codewords,
            'codebook_seed': self.codebook_seed,
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
    rs_encoded = rs_encode(framed)

    n_germs = len(rs_encoded)                                   # 1 byte / germ

    basis = OrthoBasis.build(params.half_size, params.sigma)
    codebook = design_codebook(
        basis, n_codewords=params.n_codewords, seed=params.codebook_seed,
    )

    # Map each RS-encoded byte to its codebook entry, then to theta_raw
    c_orthos = codebook[np.frombuffer(rs_encoded, dtype=np.uint8)]   # (n_germs, 5)
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
        'spike_version': '6.0',
        'filename': filename,
        'payload_size': len(payload),
        'compressed_size': len(compressed),
        'framed_size': len(framed),
        'rs_encoded_size': len(rs_encoded),
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
