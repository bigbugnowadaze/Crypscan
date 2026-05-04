"""Spike-7 encoder: spike-6 codebook modulation + calibration pilots.

Pipeline (vs spike-6):
    payload bytes
        Brotli + AXP6 header + RS(255, 223)              (unchanged)
        each byte -> codebook[byte]                       (unchanged)
        place at non-pilot grid positions                 [NEW: reserve pilots]
        place pilot anchors at pilot positions            [NEW]
        sigmoid render
        8-bit grayscale PNG
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
from pilots import select_anchor_codewords


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
    n_anchors: int = 4              # NEW: number of pilot positions

    def to_dict(self) -> dict:
        return {
            'sigma': self.sigma, 'half_size': self.half_size,
            'spacing': self.spacing, 'margin': self.margin,
            'pixel_bit_depth': self.pixel_bit_depth,
            'amp': self.amp, 'baseline': self.baseline,
            'background': self.background,
            'n_codewords': self.n_codewords,
            'codebook_seed': self.codebook_seed,
            'n_anchors': self.n_anchors,
        }


def _choose_pilot_positions(n_payload_germs: int, n_anchors: int) -> list[int]:
    """Pick n_anchors germ-positions in the grid as pilots.

    Strategy: corners of the grid first (4 positions), then mid-edges if
    n_anchors > 4. Returns indices into the linear germ-position list.
    """
    total = n_payload_germs + n_anchors
    cols = int(np.ceil(np.sqrt(total)))
    rows = (total + cols - 1) // cols
    # Corners (linear indices in the cols*rows grid):
    candidates = [
        0,                              # top-left
        cols - 1,                        # top-right
        (rows - 1) * cols,               # bottom-left
        rows * cols - 1,                 # bottom-right
        cols // 2,                       # mid-top
        (rows - 1) * cols + cols // 2,   # mid-bottom
        (rows // 2) * cols,              # mid-left
        (rows // 2) * cols + (cols - 1), # mid-right
    ]
    # Clamp to valid range and unique
    seen = set()
    chosen = []
    for c in candidates:
        c = min(c, total - 1)
        if c not in seen:
            seen.add(c)
            chosen.append(c)
        if len(chosen) >= n_anchors:
            break
    return chosen[:n_anchors]


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
    n_payload_germs = len(rs_encoded)
    n_anchors = params.n_anchors
    n_total_germs = n_payload_germs + n_anchors

    basis = OrthoBasis.build(params.half_size, params.sigma)
    codebook = design_codebook(
        basis, n_codewords=params.n_codewords, seed=params.codebook_seed,
    )

    # Pick anchor codewords spanning intensity range
    anchor_codeword_indices, anchor_patches = select_anchor_codewords(
        codebook, basis, params.amp, params.baseline,
        n_anchors=n_anchors,
    )

    # Lay out positions for n_total_germs (payload + pilots) on the grid
    positions, width, height = make_grid_positions(
        n_total_germs, spacing=params.spacing, margin=params.margin,
    )

    # Reserve some grid slots as pilot positions (corners first)
    pilot_grid_indices = _choose_pilot_positions(n_payload_germs, n_anchors)
    pilot_grid_indices_set = set(pilot_grid_indices)
    payload_grid_indices = [i for i in range(n_total_germs) if i not in pilot_grid_indices_set]

    # Map payload bytes -> codeword indices, and pilots -> anchor indices
    payload_byte_array = np.frombuffer(rs_encoded, dtype=np.uint8)
    cw_per_germ = np.zeros(n_total_germs, dtype=np.int64)
    for k, gi in enumerate(payload_grid_indices):
        cw_per_germ[gi] = int(payload_byte_array[k])
    pilot_grid_to_anchor_index = {}
    for k, gi in enumerate(pilot_grid_indices):
        anchor_idx = k % n_anchors
        cw_per_germ[gi] = anchor_codeword_indices[anchor_idx]
        pilot_grid_to_anchor_index[int(gi)] = int(anchor_idx)

    c_orthos = codebook[cw_per_germ]                          # (n_total_germs, 5)
    thetas_raw = c_orthos @ basis.M_to_raw.T

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
        'spike_version': '7.0',
        'filename': filename,
        'payload_size': len(payload),
        'compressed_size': len(compressed),
        'framed_size': len(framed),
        'rs_encoded_size': len(rs_encoded),
        'n_payload_germs': n_payload_germs,
        'n_anchors': n_anchors,
        'n_total_germs': n_total_germs,
        'width': width,
        'height': height,
        'params': params.to_dict(),
        'positions': positions.tolist(),
        'payload_grid_indices': payload_grid_indices,
        'pilot_grid_indices': pilot_grid_indices,
        'anchor_codeword_indices': [int(ci) for ci in anchor_codeword_indices],
        'pilot_grid_to_anchor_index': {
            str(k): v for k, v in pilot_grid_to_anchor_index.items()
        },
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
