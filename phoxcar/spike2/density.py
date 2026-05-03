"""CRYPSOID-faithful 2D phoxoidal density evaluator for the spike-2 carrier.

Mirrors `tools/crypsorender/math/germ.py` `phoxoidal_density_germ_full()`
(lines 194-232) at the limit of isotropic Mahalanobis:

    mahal_sq(s, t) = s^2 + t^2
    H(s, t)        = k1*s^2 + k2*t^2 + chi*(s^3 - 3st^2)
                     + omega*(3s^2t - t^3) + zeta*(s^4 + t^4)
    action(s, t)   = mahal_sq + H(s, t)^2
    intensity(s, t)= exp(-0.5 * action)

The H^2 term is the catastrophe-germ contribution that CRYPSOID's thesis
puts at the center of the substrate (`docs/thesis_digest.md` line 11).
The squaring loses the sign of H — a single bit per germ that the codec
must explicitly account for. See `germ_codec.py` for how the spike-2
encoder restores sign via a canonical convention on c_ortho[0].
"""
from __future__ import annotations
import numpy as np

from basis import OrthoBasis


def render_germ_patch_strict(
    theta_raw: np.ndarray,
    basis: OrthoBasis,
) -> np.ndarray:
    """Render one germ with CRYPSOID's strict density evaluator.

    Returns a (2*half_size+1, 2*half_size+1) float64 patch in (0, 1].
    The density evaluator caps action at 40 (matches CRYPSOID's clip in
    germ.py line 231).
    """
    H = basis.H_from_raw(theta_raw)                          # (P,)
    span = np.arange(-basis.half_size, basis.half_size + 1, dtype=np.float64)
    px, py = np.meshgrid(span, span, indexing='xy')
    s_grid = (px / basis.sigma).ravel()
    t_grid = (py / basis.sigma).ravel()
    mahal_sq = s_grid * s_grid + t_grid * t_grid
    action = np.maximum(mahal_sq + H * H, 0.0)
    # Note: spike-2 does NOT use CRYPSOID's action <= 40 clip from
    # germ.py line 231. The clip destroys information at saturated-dark
    # pixels (intensity rounds to 0 in 8-bit quantization, but after the
    # clip the fit can't distinguish action=40 from action=200). Without
    # the clip, exp(-action/2) for large action correctly underflows to
    # near-zero in float64, and the fit's log-space residual properly
    # reflects the saturation. Production substrate must reconcile this
    # with CRYPSOID's renderer.
    intensity = np.exp(-0.5 * action)
    side = 2 * basis.half_size + 1
    return intensity.reshape(side, side)


def render_carrier_strict(
    germs_raw: np.ndarray,
    positions: np.ndarray,
    width: int,
    height: int,
    basis: OrthoBasis,
    background: float = 0.0,
) -> np.ndarray:
    """Render N germs via CRYPSOID's strict density into a (height, width) carrier.

    Background defaults to 0 (consistent with the strict density model where
    "no germ" means action -> infinity, intensity -> 0). Set background=baseline
    if a non-black backdrop is desired; the inverse fit is robust either way
    since it conditions on local patch content around known positions.
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
        patch = render_germ_patch_strict(germs_raw[i], basis)
        # Strict model uses additive composition since intensity multiplies
        # against transparent background. Spike-2 grids germs with spacing >
        # 2*half_size+1 so patches don't overlap.
        canvas[y0:y1, x0:x1] = patch
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
