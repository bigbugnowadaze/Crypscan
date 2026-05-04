"""P3.A-derived spike-9B encoder: channel-matched scale (σ=8, half_size=24)
+ spatially-distributed multi-pilot layout.

Differences from P3.A encoder:
  - Larger germs: σ=8 (was 4), half_size=24 (was 12). Each germ now ~50 px
    (was ~25 px). Bandwidth concentrated below moiré beat frequency.
  - 16 pilots distributed across the canvas (was 4 in a cluster), so
    multi-region intensity-transform calibration can fit smooth-varying
    photometric drift.
  - Spacing 56 (was 28) so larger germs don't overlap.
  - Density: ~12×12 = 144 grid slots (was 26×26 = 676). Manifest 8 +
    pilots 16 = 24, leaving ~120 payload germs at 1 byte each.
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
from manifest import encode_manifest_bytes, MANIFEST_GERM_COUNT
from fiducials import (
    canonical_layout, render_markers_into_canvas,
    MARKER_SIZE_PX, MARKER_MARGIN_PX, QUIET_ZONE_PX,
)


# --- Format spec (frozen for spike-9B) -------------------------------------
CANVAS_WIDTH = 1280
CANVAS_HEIGHT = 1280

# Channel-matched germ scale (PILLAR 1 from ADDENDUM_06)
HALF_SIZE = 24
SIGMA = 8.0

# Spacing must be > 2*half_size+1 = 49. Use 56 for clean tiling.
SPACING = 56

# Multi-pilot layout: 16 pilots distributed for spatial calibration coverage
N_PILOTS = 16

# Marker zone unchanged from P3.A (these don't depend on germ scale)
MARKER_ZONE = MARKER_SIZE_PX + 2 * QUIET_ZONE_PX                    # 96+112=208
GRID_ORIGIN_X = MARKER_MARGIN_PX + MARKER_ZONE + HALF_SIZE          # 60+208+24=292
GRID_ORIGIN_Y = GRID_ORIGIN_X
GRID_END_X = CANVAS_WIDTH - GRID_ORIGIN_X
GRID_END_Y = CANVAS_HEIGHT - GRID_ORIGIN_Y
GRID_COLS = (GRID_END_X - GRID_ORIGIN_X) // SPACING + 1
GRID_ROWS = (GRID_END_Y - GRID_ORIGIN_Y) // SPACING + 1
GRID_SLOTS = GRID_COLS * GRID_ROWS


def _grid_xy(c: int, r: int) -> tuple[int, int]:
    return (GRID_ORIGIN_X + c * SPACING, GRID_ORIGIN_Y + r * SPACING)


def grid_index_to_pixel(idx: int) -> tuple[int, int]:
    if not (0 <= idx < GRID_SLOTS):
        raise ValueError(f"grid index {idx} out of range [0, {GRID_SLOTS})")
    r, c = divmod(idx, GRID_COLS)
    return _grid_xy(c, r)


def grid_rc_to_index(r: int, c: int) -> int:
    return r * GRID_COLS + c


def _build_layout() -> tuple[list[int], list[int], int]:
    """Choose specific grid indices for 16 distributed pilots + 8 manifest
    germs. Returns (pilot_indices, manifest_indices, payload_start_index_count).

    Pilot positions: 4 corners + 4 edge-midpoints + 4 inner corners + 4
    inner-quadrant centers. Designed to give every canvas-quadrant at
    least 4 pilots for the multi-pilot intensity transform fit.

    Manifest cluster: 8 germs in a row near top-left, AVOIDING any pilot
    positions.
    """
    rows = GRID_ROWS
    cols = GRID_COLS
    if rows < 8 or cols < 8:
        raise ValueError(f"grid too small for layout: {rows}×{cols}")

    pilot_rcs = [
        # 4 corners
        (0, 0), (0, cols - 1), (rows - 1, 0), (rows - 1, cols - 1),
        # 4 edge midpoints
        (0, cols // 2), (rows // 2, 0), (rows // 2, cols - 1), (rows - 1, cols // 2),
        # 4 mid-radius (between corners and center)
        (rows // 4, cols // 4), (rows // 4, 3 * cols // 4),
        (3 * rows // 4, cols // 4), (3 * rows // 4, 3 * cols // 4),
        # 4 near-center
        (rows // 2 - 1, cols // 2 - 1), (rows // 2 - 1, cols // 2 + 1),
        (rows // 2 + 1, cols // 2 - 1), (rows // 2 + 1, cols // 2 + 1),
    ]
    pilot_indices = sorted(set(grid_rc_to_index(r, c) for r, c in pilot_rcs))
    if len(pilot_indices) != N_PILOTS:
        raise ValueError(f"layout designed for {N_PILOTS} pilots but got "
                          f"{len(pilot_indices)} — adjust pilot_rcs to avoid duplicates")

    # Manifest cluster: 8 consecutive germs in row 1, starting from col 1
    # (avoids the corner pilots at row 0)
    manifest_indices = [grid_rc_to_index(1, c) for c in range(1, 1 + MANIFEST_GERM_COUNT)]
    # Verify no collision with pilots
    overlap = set(manifest_indices) & set(pilot_indices)
    if overlap:
        raise ValueError(f"manifest collides with pilots: {overlap}")
    # Payload germs: ALL remaining grid slots (in raster order), not just
    # those with index > max(reserved). This handles distributed pilots that
    # include the last-row/last-col positions.
    reserved = set(pilot_indices) | set(manifest_indices)
    payload_indices = [i for i in range(GRID_SLOTS) if i not in reserved]
    return pilot_indices, manifest_indices, payload_indices


PILOT_INDICES, MANIFEST_INDICES, PAYLOAD_INDICES = _build_layout()
PAYLOAD_CAPACITY = len(PAYLOAD_INDICES)


@dataclass
class EncodeParams:
    sigma: float = SIGMA
    half_size: int = HALF_SIZE
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


def encode(
    payload: bytes,
    filename: str,
    out_path: Path,
    params: EncodeParams | None = None,
    sidecar: bool = False,
) -> dict:
    if params is None:
        params = EncodeParams()
    out_path = Path(out_path)

    compressed = brotli.compress(payload, quality=11)
    framed = pack_header(payload, compressed, filename)
    rs_encoded = rs_encode(framed)
    n_payload_germs = len(rs_encoded)
    if n_payload_germs > PAYLOAD_CAPACITY:
        raise ValueError(
            f"payload too large for spike-9B canvas: {n_payload_germs} germs "
            f"needed, {PAYLOAD_CAPACITY} available "
            f"(reduce payload or increase canvas)"
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

    cw_per_index: dict[int, int] = {}
    for i, b in enumerate(manifest_bytes):
        cw_per_index[MANIFEST_INDICES[i]] = int(b)
    for i, ci in enumerate(anchor_codeword_indices):
        cw_per_index[PILOT_INDICES[i]] = int(ci)
    for i, b in enumerate(rs_encoded):
        cw_per_index[PAYLOAD_INDICES[i]] = int(b)

    canvas = np.full((CANVAS_HEIGHT, CANVAS_WIDTH), params.background, dtype=np.float64)
    half = basis.half_size
    for grid_idx in sorted(cw_per_index.keys()):
        cx, cy = grid_index_to_pixel(grid_idx)
        x0 = cx - half; x1 = cx + half + 1
        y0 = cy - half; y1 = cy + half + 1
        if x0 < 0 or y0 < 0 or x1 > CANVAS_WIDTH or y1 > CANVAS_HEIGHT:
            raise ValueError(f"germ {grid_idx} at ({cx},{cy}) overflows canvas")
        cw_idx = cw_per_index[grid_idx]
        theta_raw = basis.M_to_raw @ codebook[cw_idx]
        patch = render_germ_patch_sigmoid(theta_raw, basis, params.amp, params.baseline)
        canvas[y0:y1, x0:x1] = patch

    layout = canonical_layout(CANVAS_WIDTH, CANVAS_HEIGHT)
    canvas = render_markers_into_canvas(canvas, layout)
    canvas = np.clip(canvas, 0.0, 1.0)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    img = (canvas * 255.0 + 0.5).astype(np.uint8)
    Image.fromarray(img, mode='L').save(out_path, format='PNG')

    info = {
        'spike_version': 'P3B-prime.0',
        'filename': filename,
        'payload_size': len(payload),
        'compressed_size': len(compressed),
        'framed_size': len(framed),
        'rs_encoded_size': len(rs_encoded),
        'n_payload_germs': n_payload_germs,
        'canvas': [CANVAS_WIDTH, CANVAS_HEIGHT],
        'germ_grid': [GRID_COLS, GRID_ROWS, GRID_SLOTS],
        'pilots': len(PILOT_INDICES),
        'manifest_germs': len(MANIFEST_INDICES),
        'payload_capacity': PAYLOAD_CAPACITY,
        'params': params.to_dict(),
        'anchor_codeword_indices': [int(ci) for ci in anchor_codeword_indices],
        'pilot_indices': PILOT_INDICES,
        'manifest_indices': MANIFEST_INDICES,
        'fiducial': 'aruco_DICT_4X4_50',
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
        print("usage: python encoder.py <input> <output.png>")
        sys.exit(1)
    in_path = Path(sys.argv[1])
    out_path = Path(sys.argv[2])
    payload = in_path.read_bytes()
    info = encode(payload, in_path.name, out_path)
    print(json.dumps(info, indent=2))
