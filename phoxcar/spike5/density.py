"""Display-optimized phoxoidal carrier — sigmoid forward model.

    intensity(s, t) = sigmoid(baseline + amp * H(s, t))

with H(s, t) the catastrophe-germ polynomial in CRYPSOID's 5-coefficient
Pearcey-class basis (verbatim from `tools/crypsorender/math/germ.py`
lines 23-30):

    H(s, t) = k1*s^2 + k2*t^2 + chi*(s^3 - 3st^2)
              + omega*(3s^2t - t^3) + zeta*(s^4 + t^4)

# Renderer / carrier separation (Bug + ChatGPT analysis, 2026-05-03)

The proposal (`03_PHOXOIDAL_CARRIER_ARCHITECTURE.md`) originally treated
CRYPSOID's strict density evaluator and the carrier display function as
the same thing. They aren't — and don't have to be:

  CRYPSOID's strict renderer  --  for 3DGS scene rendering
                                  intensity = exp(-0.5 * (mahal + H^2))
                                  loses sign of H (1 bit/germ overhead)
                                  saturates corners at 8-bit pixel depth

  Phoxoidal carrier display   --  for an 8-bit-friendly visible carrier
                                  intensity = sigmoid(baseline + amp * H)
                                  preserves sign of H (full 40 bits/germ)
                                  bounded in (0.01, 0.99) with tuned amp

Both express the SAME 5-coefficient catastrophe-germ structure.
CRYPSOID's anti-Gaussian thesis (`docs/thesis_digest.md` line 11) is
about the catastrophe basis, not the action functional.
"""
from __future__ import annotations
import numpy as np

from basis import OrthoBasis


def sigmoid(x: np.ndarray) -> np.ndarray:
    """Numerically stable sigmoid."""
    return np.where(
        x >= 0,
        1.0 / (1.0 + np.exp(-x)),
        np.exp(x) / (1.0 + np.exp(x)),
    )


def render_germ_patch_sigmoid(
    theta_raw: np.ndarray,
    basis: OrthoBasis,
    amp: float,
    baseline: float = 0.0,
) -> np.ndarray:
    """Render one germ via the sigmoid display function.

    Returns a (2*half_size+1, 2*half_size+1) float64 patch in (0, 1).
    """
    H = basis.H_from_raw(theta_raw)
    z = baseline + amp * H
    intensity = sigmoid(z)
    side = 2 * basis.half_size + 1
    return intensity.reshape(side, side)


def render_carrier_sigmoid(
    germs_raw: np.ndarray,
    positions: np.ndarray,
    width: int,
    height: int,
    basis: OrthoBasis,
    amp: float,
    baseline: float = 0.0,
    background: float = 0.5,
) -> np.ndarray:
    """Render N germs via sigmoid display into a (height, width) carrier.

    `background` defaults to 0.5 (the center value of sigmoid(0)). Pixels
    outside any germ patch take this value. Encoder/decoder grids germs
    with spacing > 2*half_size+1 so patches don't overlap.
    """
    canvas = np.full((height, width), background, dtype=np.float64)
    germs_raw = np.asarray(germs_raw, dtype=np.float64)
    positions = np.asarray(positions, dtype=np.int64)
    if germs_raw.shape[0] != positions.shape[0]:
        raise ValueError("germs and positions must have the same length")
    half_size = basis.half_size
    for i in range(germs_raw.shape[0]):
        cx, cy = int(positions[i, 0]), int(positions[i, 1])
        x0 = cx - half_size
        x1 = cx + half_size + 1
        y0 = cy - half_size
        y1 = cy + half_size + 1
        if x0 < 0 or y0 < 0 or x1 > width or y1 > height:
            raise ValueError(
                f"germ {i} at ({cx},{cy}) overflows {width}x{height} canvas"
            )
        canvas[y0:y1, x0:x1] = render_germ_patch_sigmoid(
            germs_raw[i], basis, amp, baseline,
        )
    return canvas


def make_grid_positions(
    n_germs: int, spacing: int, margin: int
) -> tuple[np.ndarray, int, int]:
    """Lay n_germs out on a grid; carrier dimensions sized to fit."""
    cols = int(np.ceil(np.sqrt(n_germs)))
    rows = (n_germs + cols - 1) // cols
    width = margin + cols * spacing + margin
    height = margin + rows * spacing + margin
    positions = np.zeros((n_germs, 2), dtype=np.int64)
    for i in range(n_germs):
        r = i // cols
        c = i % cols
        positions[i, 0] = margin + c * spacing + spacing // 2
        positions[i, 1] = margin + r * spacing + spacing // 2
    return positions, width, height
