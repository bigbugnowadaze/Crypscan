"""End-to-end phoxcar spike-2 ENCODER (CRYPSOID-faithful).

Pipeline (vs spike-1):
    payload bytes
        -> Brotli compress                                         (same as spike-1)
        -> AXP6-equivalent inner header (header.pack_header)        (same as spike-1)
        -> RS(255, 223) byte-stream ECC                             (NEW)
        -> bit-pack into 39-bit-per-germ frames (5 bytes per germ)  (NEW)
        -> dequantize each germ to c_ortho (with c_ortho[0] >= 0)    (NEW)
        -> convert c_ortho -> theta_raw via M_to_raw                 (NEW)
        -> place at known scene positions (regular grid)
        -> render carrier via CRYPSOID's strict density evaluator    (NEW)
        -> save grayscale PNG (8-bit by default; 16-bit fallback)
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
    bit_pack_payload_to_germ_bytes, bytes_to_c_ortho,
)
from basis import OrthoBasis
from density import render_carrier_strict, make_grid_positions
from ecc import rs_encode


@dataclass
class EncodeParams:
    """Render + grid parameters. Encoder/decoder must agree."""
    sigma: float = 4.0
    half_size: int = 12
    spacing: int = 28
    margin: int = 24
    pixel_bit_depth: int = 8        # spike-2 target: 8-bit pixel depth
    background: float = 0.0          # strict density's natural "no-germ" intensity

    def to_dict(self) -> dict:
        return {
            'sigma': self.sigma, 'half_size': self.half_size,
            'spacing': self.spacing, 'margin': self.margin,
            'pixel_bit_depth': self.pixel_bit_depth,
            'background': self.background,
        }


def encode(
    payload: bytes,
    filename: str,
    out_path: Path,
    params: EncodeParams | None = None,
    sidecar: bool = True,
) -> dict:
    """Encode payload bytes to a phoxcar spike-2 PNG carrier."""
    if params is None:
        params = EncodeParams()
    out_path = Path(out_path)

    # 1. Brotli compress
    compressed = brotli.compress(payload, quality=11)

    # 2. AXP6 inner header
    framed = pack_header(payload, compressed, filename)

    # 3. Reed-Solomon ECC (between Brotli/header and germ packing)
    rs_encoded = rs_encode(framed)

    # 4. Bit-pack RS-encoded bytes into 39-bit germ frames
    germ_bytes, n_germs = bit_pack_payload_to_germ_bytes(rs_encoded)

    # 5. Build orthonormal basis (encoder/decoder must use the same params)
    basis = OrthoBasis.build(params.half_size, params.sigma)

    # 6. Dequantize each germ's 5 bytes to c_ortho (c_ortho[0] >= 0 by codec)
    c_orthos = np.zeros((n_germs, 5), dtype=np.float64)
    for g in range(n_germs):
        c_orthos[g] = bytes_to_c_ortho(germ_bytes[5 * g: 5 * (g + 1)], basis.codebook_bounds)

    # 7. Convert to theta_raw
    thetas_raw = c_orthos @ basis.M_to_raw.T

    # 7. Grid positions
    positions, width, height = make_grid_positions(
        n_germs, spacing=params.spacing, margin=params.margin,
    )

    # 8. Render via CRYPSOID's strict density
    canvas = render_carrier_strict(
        thetas_raw, positions,
        width=width, height=height, basis=basis,
        background=params.background,
    )

    # 9. Save as PNG
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
        'spike_version': '2.0',
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
        print("usage: python encoder.py <input_file> <output.png> [bit_depth]")
        sys.exit(1)
    in_path = Path(sys.argv[1])
    out_path = Path(sys.argv[2])
    depth = int(sys.argv[3]) if len(sys.argv) >= 4 else 8
    payload = in_path.read_bytes()
    mf = encode(payload, in_path.name, out_path, params=EncodeParams(pixel_bit_depth=depth))
    print(json.dumps({k: v for k, v in mf.items() if k != 'positions'}, indent=2))
