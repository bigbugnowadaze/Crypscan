"""Synthetic 2D germ renderer for the phoxcar spike.

Forward model (linear-in-coefficients, sign-preserving):

    intensity(s, t) = baseline
                    + amp * exp(-0.5 * (s**2 + t**2)) * H(s, t)

with the catastrophe germ

    H(s, t) = k1*s**2 + k2*t**2 + chi*(s**3 - 3*s*t**2)
              + omega*(3*s**2*t - t**3) + zeta*(s**4 + t**4)

and local coords (s, t) = ((px - cx) / sigma, (py - cy) / sigma).

# Why not the strict CRYPSOID density evaluator?

CRYPSOID's `phoxoidal_density_germ_full` (germ.py lines 194-232) uses
`action = mahal_sq + H**2` -> `intensity = exp(-0.5 * action)`. That is
the right *production* model — but it loses the sign of H (since H is
squared in the action), which costs ~1 bit per germ to a sign convention
or a sign-bit overhead in the codec. The spike chooses a linear forward
model that:

  - is sign-preserving (decoder recovers the full coefficient vector
    including signs)
  - is linear in the 5 coefficients (inverse fit is plain linear LSQ)
  - approximates CRYPSOID's full evaluator in the small-H limit
    (exp(-0.5 * H**2) ~= 1 - 0.5*H**2; the linear order matches if we
    multiply by the Gaussian envelope)

This is a spike-specific simplification documented in the README and
in `ADDENDUM_01_img2phox_integration.md` `06_DECODER_RESEARCH_PLAN`
follow-on. Phase 1's production decoder must handle CRYPSOID's full
evaluator (Newton solve or similar).
"""
from __future__ import annotations
import numpy as np


def germ_eval(germ: np.ndarray, s: np.ndarray, t: np.ndarray) -> np.ndarray:
    """Evaluate H(s, t) for a single 5-coef germ on broadcast grids."""
    k1, k2, chi, omega, zeta = germ
    s2 = s * s
    t2 = t * t
    return (
        k1 * s2
        + k2 * t2
        + chi * (s * s2 - 3.0 * s * t2)
        + omega * (3.0 * s2 * t - t * t2)
        + zeta * (s2 * s2 + t2 * t2)
    )


def germ_basis(s: np.ndarray, t: np.ndarray) -> np.ndarray:
    """Stack the 5 basis functions [s^2, t^2, s^3-3st^2, 3s^2t-t^3, s^4+t^4].

    Returns array with shape s.shape + (5,).
    """
    s2 = s * s
    t2 = t * t
    return np.stack([
        s2,
        t2,
        s * s2 - 3.0 * s * t2,
        3.0 * s2 * t - t * t2,
        s2 * s2 + t2 * t2,
    ], axis=-1)


def render_germ_patch(
    germ: np.ndarray,
    sigma: float,
    half_size: int,
    amp: float,
    baseline: float = 0.5,
) -> np.ndarray:
    """Render one germ's intensity profile into a (2*half_size+1)^2 patch."""
    span = np.arange(-half_size, half_size + 1, dtype=np.float64)
    px, py = np.meshgrid(span, span, indexing='xy')
    s = px / sigma
    t = py / sigma
    H = germ_eval(germ, s, t)
    envelope = np.exp(-0.5 * (s * s + t * t))
    return (baseline + amp * envelope * H).astype(np.float32)


def render_carrier(
    germs: np.ndarray,
    positions: np.ndarray,
    width: int,
    height: int,
    sigma: float,
    half_size: int,
    amp: float,
    baseline: float = 0.5,
) -> np.ndarray:
    """Render N germs into a (height, width) carrier image.

    Args:
        germs: (N, 5) coefficients.
        positions: (N, 2) integer pixel positions (x, y).
        width, height: carrier image size in pixels.
        sigma: spatial scale for the Mahalanobis envelope.
        half_size: per-germ patch half-window. Patch is (2*half_size+1)^2.
        amp: amplitude scaling for the H modulation.
        baseline: background intensity in [0, 1].

    Returns:
        (height, width) float32 carrier in [0, 1].
    """
    canvas = np.full((height, width), baseline, dtype=np.float32)
    germs = np.asarray(germs, dtype=np.float64)
    positions = np.asarray(positions, dtype=np.int64)
    if germs.shape[0] != positions.shape[0]:
        raise ValueError("germs and positions must have the same length")

    for i in range(germs.shape[0]):
        cx, cy = positions[i]
        x0 = cx - half_size
        x1 = cx + half_size + 1
        y0 = cy - half_size
        y1 = cy + half_size + 1
        if x0 < 0 or y0 < 0 or x1 > width or y1 > height:
            raise ValueError(
                f"germ {i} at ({cx},{cy}) with half_size={half_size} "
                f"overflows {width}x{height} canvas"
            )
        patch = render_germ_patch(germs[i], sigma, half_size, amp, baseline)
        # Replace canvas with the patch — the spike grids germs at spacing
        # > 2*half_size+1 so patches don't overlap.
        canvas[y0:y1, x0:x1] = patch
    return np.clip(canvas, 0.0, 1.0)


def make_grid_positions(
    n_germs: int, spacing: int, margin: int
) -> tuple[np.ndarray, int, int]:
    """Lay n_germs out on a grid with the given spacing.

    Returns:
        positions (N, 2), width, height.
    """
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
