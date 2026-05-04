"""Spike-8A encoder: spike-7 substrate + finder corners + manifest cluster.

NO JSON SIDECAR REQUIRED FOR DECODE. The decoder uses only the format
specification (canvas size, finder positions, grid layout) plus what it
reads from the manifest cluster in the rectified image.

Pipeline:
    payload bytes
      Brotli + AXP6 header + RS(255, 223)         (frozen layers 1-2)
      manifest cluster (8 germs encoding RS-encoded byte count)
      4 calibration pilots                          (frozen layer 4)
      payload germs (1 byte / germ via codebook)   (frozen layer 3)
      4 finder corners (saturating glyphs)         [NEW: layer 5]
      sigmoid render onto fixed 1280x1280 canvas   (frozen layer 6)
      8-bit grayscale PNG                           (frozen layer 8)

Canonical canvas size is FIXED in the spike-8A format spec. Variable
payload sizes consume more of the inner grid; unused positions are not
rendered.
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
from density import render_germ_patch_sigmoid
from ecc import rs_encode
from codebook import design_codebook
from pilots import select_anchor_codewords
from finders import (
    FINDER_AMP, FINDER_GLYPH_A, FINDER_GLYPH_B,
    FINDER_MARGIN, render_finders_into_canvas,
    canonical_finder_positions,
)
from manifest import (
    encode_manifest_bytes, MANIFEST_GERM_COUNT,
)


# --- Format spec (frozen for spike-8A) --------------------------------------
CANVAS_WIDTH = 1280
CANVAS_HEIGHT = 1280
SPACING = 28
INNER_MARGIN = 60        # px from finder center to first inner germ
N_PILOTS = 4

GRID_ORIGIN_X = FINDER_MARGIN + INNER_MARGIN
GRID_ORIGIN_Y = FINDER_MARGIN + INNER_MARGIN
GRID_END_X = CANVAS_WIDTH - GRID_ORIGIN_X
GRID_END_Y = CANVAS_HEIGHT - GRID_ORIGIN_Y
GRID_COLS = (GRID_END_X - GRID_ORIGIN_X) // SPACING + 1
GRID_ROWS = (GRID_END_Y - GRID_ORIGIN_Y) // SPACING + 1
GRID_SLOTS = GRID_COLS * GRID_ROWS

MANIFEST_INDICES = list(range(MANIFEST_GERM_COUNT))            # 0..7
PILOT_INDICES = list(range(MANIFEST_GERM_COUNT,
                            MANIFEST_GERM_COUNT + N_PILOTS))   # 8..11
PAYLOAD_START_INDEX = MANIFEST_GERM_COUNT + N_PILOTS           # 12


@dataclass
class EncodeParams:
    sigma: float = 4.0
    half_size: int = 12
    pixel_bit_depth: int = 8
    amp: float = 0.30
    baseline: float = 0.0
    background: float = 0.5
    n_codewords: int = 256
    codebook_seed: int = 20260504

    def to_dict(self) -> dict:
        return {
            'sigma': self.sigma, 'half_size': self.half_size,
            'pixel_bit_depth': self.pixel_bit_depth,
            'amp': self.amp, 'baseline': self.baseline,
            'background': self.background,
            'n_codewords': self.n_codewords,
            'codebook_seed': self.codebook_seed,
        }


def grid_index_to_pixel(idx: int) -> tuple[int, int]:
    """Convert a grid index (0..GRID_SLOTS-1) to (x, y) pixel coords."""
    if not (0 <= idx < GRID_SLOTS):
        raise ValueError(f"grid index {idx} out of range [0, {GRID_SLOTS})")
    r = idx // GRID_COLS
    c = idx % GRID_COLS
    return GRID_ORIGIN_X + c * SPACING, GRID_ORIGIN_Y + r * SPACING


def encode(
    payload: bytes,
    filename: str,
    out_path: Path,
    params: EncodeParams | None = None,
    sidecar: bool = True,
) -> dict:
    """Encode `payload` to a phoxcar PNG carrier.

    The sidecar (manifest.json) is *informational* only — it records
    encode-time data for diagnostic purposes. The decoder does NOT use
    it; spike-8A's decoder reads only the in-carrier manifest cluster.
    """
    if params is None:
        params = EncodeParams()
    out_path = Path(out_path)

    compressed = brotli.compress(payload, quality=11)
    framed = pack_header(payload, compressed, filename)
    rs_encoded = rs_encode(framed)
    n_payload_germs = len(rs_encoded)
    n_used_germs = PAYLOAD_START_INDEX + n_payload_germs
    if n_used_germs > GRID_SLOTS:
        raise ValueError(
            f"payload too large for spike-8A canvas: needs {n_used_germs} "
            f"grid slots, only {GRID_SLOTS} available"
        )

    basis = OrthoBasis.build(params.half_size, params.sigma)
    codebook = design_codebook(
        basis, n_codewords=params.n_codewords, seed=params.codebook_seed,
    )
    anchor_codeword_indices, _ = select_anchor_codewords(
        codebook, basis, params.amp, params.baseline,
        n_anchors=N_PILOTS,
    )

    manifest_bytes = encode_manifest_bytes(payload_byte_count=n_payload_germs)

    # --- Build the (germ_index -> codeword_index) map ----------------------
    cw_per_index = {}
    # Manifest germs (8 bytes -> 8 codewords)
    for i, b in enumerate(manifest_bytes):
        cw_per_index[MANIFEST_INDICES[i]] = int(b)
    # Pilot germs (4 anchor codewords)
    for i, ci in enumerate(anchor_codeword_indices):
        cw_per_index[PILOT_INDICES[i]] = int(ci)
    # Payload germs
    for i, b in enumerate(rs_encoded):
        cw_per_index[PAYLOAD_START_INDEX + i] = int(b)

    # --- Render: prepare flat canvas, then place germ patches ---------------
    canvas = np.full((CANVAS_HEIGHT, CANVAS_WIDTH), params.background, dtype=np.float64)
    half = basis.half_size
    for grid_idx in sorted(cw_per_index.keys()):
        cx, cy = grid_index_to_pixel(grid_idx)
        x0 = cx - half
        x1 = cx + half + 1
        y0 = cy - half
        y1 = cy + half + 1
        if x0 < 0 or y0 < 0 or x1 > CANVAS_WIDTH or y1 > CANVAS_HEIGHT:
            raise ValueError(
                f"germ at grid_idx={grid_idx} ({cx},{cy}) overflows canvas"
            )
        cw_idx = cw_per_index[grid_idx]
        theta_raw = basis.M_to_raw @ codebook[cw_idx]
        patch = render_germ_patch_sigmoid(theta_raw, basis, params.amp, params.baseline)
        canvas[y0:y1, x0:x1] = patch

    # --- Render finders OVER existing germs (they sit at exclusion zones) --
    canvas = render_finders_into_canvas(canvas, codebook, basis, FINDER_MARGIN)

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

    info = {
        'spike_version': '8A.0',
        'filename': filename,
        'payload_size': len(payload),
        'compressed_size': len(compressed),
        'framed_size': len(framed),
        'rs_encoded_size': len(rs_encoded),
        'n_payload_germs': n_payload_germs,
        'n_used_germs': n_used_germs,
        'canvas': [CANVAS_WIDTH, CANVAS_HEIGHT],
        'params': params.to_dict(),
        'anchor_codeword_indices': [int(ci) for ci in anchor_codeword_indices],
    }
    if sidecar:
        sidecar_path = out_path.with_suffix(out_path.suffix + '.info.json')
        sidecar_path.write_text(json.dumps(info, indent=2))
    info['png_path'] = str(out_path)
    info['png_bytes'] = out_path.stat().st_size
    return info


if __name__ == '__main__':
    import sys
    if len(sys.argv) < 3:
        print("usage: python encoder.py <input> <output.png> [bit_depth]")
        sys.exit(1)
    in_path = Path(sys.argv[1])
    out_path = Path(sys.argv[2])
    depth = int(sys.argv[3]) if len(sys.argv) >= 4 else 8
    payload = in_path.read_bytes()
    info = encode(payload, in_path.name, out_path,
                   params=EncodeParams(pixel_bit_depth=depth))
    print(json.dumps(info, indent=2))
