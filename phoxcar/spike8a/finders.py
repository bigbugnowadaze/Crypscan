"""Corner finder design for spike-8A.

Four corner markers placed at known canonical positions, used by the
decoder to recover homography from a captured/warped image without
a JSON sidecar.

# Design

Each finder is a phoxoidal germ rendered at ELEVATED amplitude
(amp_finder = 0.50 vs payload amp = 0.30) so the finder patch
saturates more aggressively than payload germs. Combined with a
specific finder codebook glyph chosen for high-contrast intensity
profile, the finders are visually distinctive bright/dark blobs.

Asymmetry: 3 finders use FINDER_GLYPH_A; the SE corner uses
FINDER_GLYPH_B. The decoder identifies SE by its slightly different
intensity signature, then assigns NW/NE/SW by relative position.

Decoder pipeline:
    blob_log on Gaussian-smoothed carrier
        -> filter blobs by intensity + size
        -> sort to identify 4 corners
        -> identify SE by signature
        -> 4-point homography (canonical -> observed)
        -> rectify
"""
from __future__ import annotations
import numpy as np

from basis import OrthoBasis
from density import render_germ_patch_sigmoid
from codebook import design_codebook


# --- Finder configuration (frozen for spike-8A) -----------------------------
# At payload amp=0.30, ~99% of payload germs have <7% bright (>0.95) pixels.
# At finder amp=1.0, glyph 143 has 38.7% bright pixels — a 5x discriminator
# usable for connected-component-based detection via area filtering.
FINDER_AMP = 1.00            # saturating; payload uses 0.30
FINDER_GLYPH_A = 143         # 38.7% pixels >0.95 at amp=1.0; used for NW/NE/SW
FINDER_GLYPH_B = 13          # 37.1% pixels >0.95 at amp=1.0; SE orientation marker
FINDER_MARGIN = 36           # pixels from carrier edge to finder center


def render_finder_patch(
    finder_glyph: int,
    codebook: np.ndarray,
    basis: OrthoBasis,
) -> np.ndarray:
    """Render a finder patch at FINDER_AMP."""
    theta_raw = basis.M_to_raw @ codebook[finder_glyph]
    return render_germ_patch_sigmoid(theta_raw, basis, amp=FINDER_AMP, baseline=0.0)


def canonical_finder_positions(
    payload_grid_width: int,
    payload_grid_height: int,
    margin: int = FINDER_MARGIN,
) -> dict:
    """Return dict mapping {'NW', 'NE', 'SW', 'SE'} to (x, y) finder centers.

    Finder corners sit AT the edge of the carrier, OUTSIDE the payload grid
    region. The payload grid lives in the interior with its own margin.
    """
    return {
        'NW': (margin, margin),
        'NE': (payload_grid_width - margin - 1, margin),
        'SW': (margin, payload_grid_height - margin - 1),
        'SE': (payload_grid_width - margin - 1, payload_grid_height - margin - 1),
    }


def render_finders_into_canvas(
    canvas: np.ndarray,
    codebook: np.ndarray,
    basis: OrthoBasis,
    margin: int = FINDER_MARGIN,
) -> np.ndarray:
    """Render the 4 corner finders into the canvas (in place AND return).

    canvas: (H, W) float64 array assumed pre-baselined.
    """
    h, w = canvas.shape
    positions = canonical_finder_positions(w, h, margin)
    half = basis.half_size
    for corner, (cx, cy) in positions.items():
        glyph = FINDER_GLYPH_B if corner == 'SE' else FINDER_GLYPH_A
        patch = render_finder_patch(glyph, codebook, basis)
        x0 = cx - half
        x1 = cx + half + 1
        y0 = cy - half
        y1 = cy + half + 1
        # Clip to canvas bounds (finders sit at edge — patch may overflow if margin < half_size)
        if x0 < 0 or y0 < 0 or x1 > w or y1 > h:
            raise ValueError(
                f"finder at ({cx},{cy}) with half_size={half} overflows {w}x{h} "
                f"(margin {margin} must be >= half_size={half})"
            )
        canvas[y0:y1, x0:x1] = patch
    return canvas
