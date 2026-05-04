"""Phoxoidal-native pose recovery for P3.B.

Pipeline:
    captured image (8-bit grayscale, [0, 1] floats internally)
      -> for each corner ('NW', 'NE', 'SW', 'SE'):
           -> render the canonical 3x3 cluster template for that corner
           -> for each scale in CORNER_SEARCH_SCALES:
                resize template by scale
                compute normalized cross-correlation (NCC) against captured
                find peak (max NCC) location AND score
           -> pick the best scale; record (peak_x, peak_y, peak_score)
      -> sanity check: 4 peak scores all above CORNER_NCC_THRESHOLD
                        AND 4 peaks form a "reasonable" quadrilateral
                        (each peak in roughly the right canvas quadrant)
      -> 4-point homography (observed peak centers -> canonical centers)
      -> rectify via cv2.warpPerspective

# Why NCC matched filter?

NCC is invariant to additive (brightness) and multiplicative (contrast)
photometric drift by construction:

    NCC(I, T) = sum (I - mean_I)(T - mean_T) / sqrt(var_I * var_T)

So the photometric envelope is opened "for free" — the detector is
brightness/contrast-blind. Gamma is the only photometric channel that
can degrade NCC, because it warps relative pixel ratios within a
template.

Thesis-aligned: the detector kernel IS the catastrophe-germ basis.
We are detecting "carrier germs" using the carrier-germ template.
Phoxoidal-native end-to-end.

# Multi-scale search

The captured image may be at a different scale than the canonical
canvas (capture distance, zoom). Try a small set of scale factors
[0.7, 0.85, 1.0, 1.18, 1.4]; pick the scale whose NCC peak is highest.

# Quadrant gating

After detection, NW peak should be in the top-left quadrant of the
captured image; NE in top-right; SW in bottom-left; SE in bottom-right.
This is a sanity check, not an identity check (identity comes from the
template glyph distinctiveness).
"""
from __future__ import annotations
from dataclasses import dataclass, field
import numpy as np
import cv2

from basis import OrthoBasis
from fiducials import (
    CornerLayout, canonical_layout,
    CORNER_GLYPHS, render_cluster_template, cluster_size_px,
)


# Multi-scale search range (factors applied to canonical cluster size)
CORNER_SEARCH_SCALES = (0.7, 0.85, 1.0, 1.18, 1.4)
# NCC peak threshold below which the corner is considered "not found"
CORNER_NCC_THRESHOLD = 0.40
# Quadrant tolerance: a corner peak is OK if it's anywhere in its half of
# the image (top vs bottom, left vs right). Set to 0.0 to disable gating.
QUADRANT_GATING = True


@dataclass
class CornerDetection:
    name: str               # 'NW' | 'NE' | 'SW' | 'SE'
    peak_xy: tuple[float, float] | None
    peak_score: float       # max NCC value (-1..1)
    best_scale: float


@dataclass
class PoseResult:
    success: bool
    homography: np.ndarray | None
    observed_centers: dict | None
    detections: list = field(default_factory=list)
    error: str | None = None


def _ncc_match_at_scale(image: np.ndarray, template: np.ndarray, scale: float) -> tuple[tuple[float, float], float]:
    """Run NCC of `template` resized by `scale` over `image`. Returns (peak_xy, peak_score)."""
    if scale != 1.0:
        new_h = max(3, int(round(template.shape[0] * scale)))
        new_w = max(3, int(round(template.shape[1] * scale)))
        T = cv2.resize(template, (new_w, new_h), interpolation=cv2.INTER_LINEAR)
    else:
        T = template
    if T.shape[0] >= image.shape[0] or T.shape[1] >= image.shape[1]:
        return ((0.0, 0.0), -1.0)
    img = image.astype(np.float32)
    tmpl = T.astype(np.float32)
    res = cv2.matchTemplate(img, tmpl, cv2.TM_CCOEFF_NORMED)
    _min_val, max_val, _min_loc, max_loc = cv2.minMaxLoc(res)
    # max_loc is (x, y) of TOP-LEFT of the matched template location.
    # Convert to template CENTER:
    cx = max_loc[0] + tmpl.shape[1] / 2.0
    cy = max_loc[1] + tmpl.shape[0] / 2.0
    return ((cx, cy), float(max_val))


def _quadrant_ok(corner_name: str, peak_xy: tuple[float, float],
                  image_w: int, image_h: int) -> bool:
    """Gate: NW peak in top-left half, NE in top-right, etc."""
    if not QUADRANT_GATING:
        return True
    cx, cy = peak_xy
    mid_x = image_w / 2.0
    mid_y = image_h / 2.0
    if corner_name == 'NW':
        return cx < mid_x and cy < mid_y
    if corner_name == 'NE':
        return cx >= mid_x and cy < mid_y
    if corner_name == 'SW':
        return cx < mid_x and cy >= mid_y
    if corner_name == 'SE':
        return cx >= mid_x and cy >= mid_y
    return False


def detect_pose(captured: np.ndarray,
                  basis: OrthoBasis,
                  layout: CornerLayout) -> PoseResult:
    """Detect 4 corner clusters in a captured image and recover homography.

    Args:
        captured: (H, W) grayscale image in [0, 1].
        basis: same OrthoBasis used by the encoder.
        layout: canonical CornerLayout for the encoder's canvas.

    Returns:
        PoseResult.success=True iff all 4 corners detected above threshold
        and in the correct quadrants (when gating enabled).
    """
    h, w = captured.shape

    # Render canonical templates once for each corner
    templates = {
        name: render_cluster_template(theta_raw, basis)
        for name, theta_raw in CORNER_GLYPHS.items()
    }

    detections: list[CornerDetection] = []
    observed_centers: dict[str, tuple[float, float]] = {}

    for corner_name in ('NW', 'NE', 'SW', 'SE'):
        T = templates[corner_name]
        best_score = -np.inf
        best_xy = None
        best_scale = 1.0
        for scale in CORNER_SEARCH_SCALES:
            peak_xy, peak_score = _ncc_match_at_scale(captured, T, scale)
            if peak_score > best_score and _quadrant_ok(corner_name, peak_xy, w, h):
                best_score = peak_score
                best_xy = peak_xy
                best_scale = scale
        detections.append(CornerDetection(
            name=corner_name, peak_xy=best_xy,
            peak_score=float(best_score) if np.isfinite(best_score) else -1.0,
            best_scale=best_scale,
        ))
        if best_xy is not None and best_score >= CORNER_NCC_THRESHOLD:
            observed_centers[corner_name] = best_xy

    if len(observed_centers) < 4:
        weak = [d.name for d in detections if d.peak_score < CORNER_NCC_THRESHOLD]
        return PoseResult(
            success=False, homography=None, observed_centers=None,
            detections=detections,
            error=f"weak corners (NCC < {CORNER_NCC_THRESHOLD}): {weak}",
        )

    canonical = layout.corner_centers()
    src = np.array([observed_centers[k] for k in ('NW', 'NE', 'SW', 'SE')], dtype=np.float32)
    dst = np.array([canonical[k] for k in ('NW', 'NE', 'SW', 'SE')], dtype=np.float32)
    H, _ = cv2.findHomography(src, dst, method=0)
    if H is None:
        return PoseResult(
            success=False, homography=None, observed_centers=observed_centers,
            detections=detections, error="findHomography failed",
        )
    return PoseResult(
        success=True, homography=H, observed_centers=observed_centers,
        detections=detections, error=None,
    )


def rectify(captured: np.ndarray,
              homography: np.ndarray,
              canvas_w: int, canvas_h: int,
              fill: float = 0.5) -> np.ndarray:
    """Warp the captured image to canonical (canvas_h, canvas_w) coords."""
    src = captured.astype(np.float32) if captured.dtype != np.float32 else captured
    rectified = cv2.warpPerspective(
        src, homography, (canvas_w, canvas_h),
        flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT,
        borderValue=fill,
    )
    return rectified
