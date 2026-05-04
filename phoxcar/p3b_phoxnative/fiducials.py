"""Phoxoidal-native fiducial layer for P3.B.

Replaces P3.A's ArUco markers with catastrophe-germ-native corner
clusters detected by matched-filter NCC against germ templates.

# Why phoxoidal-native?

The hybrid-identity addendum (`phoxoidal_carrier_proposal/ADDENDUM_02_hybrid_identity.md`)
acknowledges that P3.A's pose layer is conventional CV (ArUco), not
catastrophe-germ-native. P3.B is the research path to retire that
dependency: pose recovery using ONLY the catastrophe-germ basis.

# Design

Each corner = a 3x3 CLUSTER of identical phoxoidal germs rendered at
high amp (1.0). Four different extremal-coefficient germs are used,
one per corner, so the detector can identify which cluster is which
by template-matching.

Cluster geometry (canonical canvas):
  - Cluster footprint: 3x3 germs, spacing = 2*half_size+1 = 25 px
    (so adjacent germ patches abut without overlap or gap).
  - Cluster outer extent: 3 * 25 = 75 px wide.
  - Corner cluster center: MARKER_MARGIN_PX + cluster_extent/2 from edge.
  - "Quiet zone": carrier baseline (0.5) around each cluster — the
    matched-filter detector handles the unstructured-background case
    without needing an ArUco-style hard white border.

Corner germ choice (extremal raw coefficients):
  NW glyph:  (+1.0, -1.0,    0,    0,    0)  diagonal saddle
  NE glyph:  (-1.0, +1.0,    0,    0,    0)  opposite diagonal saddle
  SW glyph:  (   0,    0, +1.0,    0,    0)  3-fold cubic ("trefoil")
  SE glyph:  (   0,    0,    0, +1.0,    0)  3-fold cubic, rotated

These are at the L_inf=1.0 bound of theta_raw, so they saturate the
sigmoid display. The 4 patterns are:
  - Mutually distinct under NCC (different basis functions; cross-NCC
    is small)
  - Each visually identifiable (extremal saddle vs trefoil patterns)

Limitations of this design (acknowledged for V3 frontier):
  - Saddle germs have 180° rotational symmetry → if carrier is
    rotated 180° between encode and decode, NW and NE clusters become
    indistinguishable. P3.B's first-iteration target is in-plane
    rotation small (< 45°); large rotations are deferred to a P3.C
    iteration that uses fully-asymmetric corner glyphs.
  - Trefoil germs have 120° rotational symmetry → same caveat for
    extreme rotation.

# Encoder API (used by encoder.py)

  CORNER_AMP, CORNER_HALF_SIZE, CORNER_GERMS_PER_SIDE,
  CORNER_GERM_SPACING, CORNER_CLUSTER_MARGIN_PX
  CORNER_GLYPHS                  -> {'NW':theta_raw, 'NE':..., 'SW':..., 'SE':...}
  canonical_corner_centers(w, h) -> {'NW':(cx,cy), ...}
  render_cluster_template(theta_raw, basis) -> (cluster_h, cluster_w) float32
  render_corners_into_canvas(canvas, basis) -> canvas (in place + return)
"""
from __future__ import annotations
from dataclasses import dataclass
import numpy as np

from basis import OrthoBasis
from density import render_germ_patch_sigmoid


# --- Frozen P3.B corner config ----------------------------------------------
CORNER_AMP = 1.00                  # saturating sigmoid; payload uses 0.30
CORNER_GERMS_PER_SIDE = 3          # 3x3 cluster
CORNER_GERM_SPACING = 25            # = 2*half_size+1 for half_size=12 -> patches abut
CORNER_CLUSTER_MARGIN_PX = 60       # cluster center distance from canvas edge
                                     # (matches P3.A's MARKER_MARGIN_PX + half-cluster)

# Extremal-coefficient corner glyphs (theta_raw, 5-vector at L_inf=1.0)
CORNER_GLYPHS = {
    'NW': np.array([+1.0, -1.0,  0.0,  0.0,  0.0], dtype=np.float64),
    'NE': np.array([-1.0, +1.0,  0.0,  0.0,  0.0], dtype=np.float64),
    'SW': np.array([ 0.0,  0.0, +1.0,  0.0,  0.0], dtype=np.float64),
    'SE': np.array([ 0.0,  0.0,  0.0, +1.0,  0.0], dtype=np.float64),
}


@dataclass
class CornerLayout:
    """Canonical positions of the 4 corner cluster CENTERS on the canvas."""
    nw_xy: tuple[int, int]
    ne_xy: tuple[int, int]
    sw_xy: tuple[int, int]
    se_xy: tuple[int, int]
    cluster_size_px: int

    def corner_centers(self) -> dict[str, tuple[float, float]]:
        return {
            'NW': (float(self.nw_xy[0]), float(self.nw_xy[1])),
            'NE': (float(self.ne_xy[0]), float(self.ne_xy[1])),
            'SW': (float(self.sw_xy[0]), float(self.sw_xy[1])),
            'SE': (float(self.se_xy[0]), float(self.se_xy[1])),
        }


def cluster_size_px(half_size: int) -> int:
    """Side length of a 3x3 corner cluster in pixels."""
    germ_side = 2 * half_size + 1
    return CORNER_GERMS_PER_SIDE * germ_side


def canonical_layout(canvas_w: int, canvas_h: int,
                       half_size: int = 12,
                       margin_px: int = CORNER_CLUSTER_MARGIN_PX) -> CornerLayout:
    cs = cluster_size_px(half_size)
    half_cluster = cs // 2
    cx_nw = margin_px + half_cluster
    cy_nw = margin_px + half_cluster
    cx_ne = canvas_w - margin_px - half_cluster
    cy_ne = margin_px + half_cluster
    cx_sw = margin_px + half_cluster
    cy_sw = canvas_h - margin_px - half_cluster
    cx_se = canvas_w - margin_px - half_cluster
    cy_se = canvas_h - margin_px - half_cluster
    return CornerLayout(
        nw_xy=(cx_nw, cy_nw),
        ne_xy=(cx_ne, cy_ne),
        sw_xy=(cx_sw, cy_sw),
        se_xy=(cx_se, cy_se),
        cluster_size_px=cs,
    )


def render_cluster_template(theta_raw: np.ndarray,
                              basis: OrthoBasis,
                              amp: float = CORNER_AMP,
                              baseline_clear: float = 0.5) -> np.ndarray:
    """Render a 3x3 cluster of identical germs as a single template image.

    The patches abut (spacing = 2*half_size+1). Returns a float32 image
    of shape (cluster_size_px, cluster_size_px) in [0, 1].

    `baseline_clear` only affects the (rare) case where rounding leaves
    a 1-pixel gap; the clusters are designed so patches tile exactly.
    """
    germ_side = 2 * basis.half_size + 1
    cluster = cluster_size_px(basis.half_size)
    template = np.full((cluster, cluster), baseline_clear, dtype=np.float64)
    patch = render_germ_patch_sigmoid(theta_raw, basis, amp=amp, baseline=0.0)
    for r in range(CORNER_GERMS_PER_SIDE):
        for c in range(CORNER_GERMS_PER_SIDE):
            y0 = r * germ_side
            x0 = c * germ_side
            template[y0:y0 + germ_side, x0:x0 + germ_side] = patch
    return template.astype(np.float32)


def render_corners_into_canvas(canvas: np.ndarray,
                                  basis: OrthoBasis,
                                  layout: CornerLayout) -> np.ndarray:
    """Render the 4 corner clusters onto the canvas (in place AND return).

    Each cluster is centered at the canonical (cx, cy) for that corner.
    The corners overwrite whatever payload-grid content was there
    (encoder must keep the corner-zone slots empty in its grid layout).
    """
    h, w = canvas.shape
    cluster = layout.cluster_size_px
    half = cluster // 2
    placements = [
        ('NW', layout.nw_xy),
        ('NE', layout.ne_xy),
        ('SW', layout.sw_xy),
        ('SE', layout.se_xy),
    ]
    for corner_name, (cx, cy) in placements:
        theta_raw = CORNER_GLYPHS[corner_name]
        template = render_cluster_template(theta_raw, basis)
        x0 = cx - half
        y0 = cy - half
        x1 = x0 + cluster
        y1 = y0 + cluster
        if x0 < 0 or y0 < 0 or x1 > w or y1 > h:
            raise ValueError(
                f"corner {corner_name} cluster at ({cx},{cy}) overflows {w}x{h} canvas"
            )
        canvas[y0:y1, x0:x1] = template
    return canvas
