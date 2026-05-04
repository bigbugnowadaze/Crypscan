"""Pilots module for spike-9B — supports multi-pilot spatially-distributed
calibration (pillar 3 of ADDENDUM_06).

Re-exports verbatim spike-7+'s pilot fit interface from `pilots_base.py`
(the original p3a_aruco/pilots.py copied verbatim) and adds:
  - fit_local_intensity_transforms — fits one transform per spatial
    region (e.g. per canvas quadrant) given pilots distributed across
    those regions.
  - LocalIntensityTransformGrid — holds K transforms + an
    invert(image) method that picks the right transform per region.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Sequence
import numpy as np

from pilots_base import (
    IntensityTransform, fit_intensity_transform, gather_anchor_pixels,
    select_anchor_codewords,
)


@dataclass
class LocalIntensityTransformGrid:
    """K spatially-distributed intensity transforms, one per region.

    Regions are axis-aligned rectangles tiling the canvas. Each region has
    its own (a, b, gamma) fit. When `invert(image, x, y)` is called, the
    transform from the region containing (x, y) is used.

    For spike-9B, a 2×2 quadrant tiling is the default (4 regions, 4
    pilots each).
    """
    transforms: list[IntensityTransform]      # K transforms, raster order
    region_x_edges: tuple[int, ...]           # K_x+1 x-edges
    region_y_edges: tuple[int, ...]           # K_y+1 y-edges
    canvas_w: int
    canvas_h: int

    def _region_index(self, x: int, y: int) -> int:
        """Region index for a (x, y) point. Raster order, K_y rows of K_x."""
        kx = max(0, min(len(self.region_x_edges) - 2,
                          int(np.searchsorted(self.region_x_edges, x, side='right') - 1)))
        ky = max(0, min(len(self.region_y_edges) - 2,
                          int(np.searchsorted(self.region_y_edges, y, side='right') - 1)))
        n_x = len(self.region_x_edges) - 1
        return ky * n_x + kx

    def invert_at(self, observed_value: float, x: int, y: int) -> float:
        idx = self._region_index(x, y)
        return float(self.transforms[idx].invert(np.array([observed_value]))[0])

    def invert(self, image: np.ndarray) -> np.ndarray:
        """Invert the entire image via spatially-varying transform.

        Computes per-region inverse and stitches. Edges between regions
        are HARD (no smooth interpolation) — for spike-9B v0 this is
        adequate; smooth-varying interpolation is a follow-up if needed.
        """
        out = np.empty_like(image, dtype=np.float32)
        n_x = len(self.region_x_edges) - 1
        n_y = len(self.region_y_edges) - 1
        for ky in range(n_y):
            y0 = self.region_y_edges[ky]
            y1 = self.region_y_edges[ky + 1]
            for kx in range(n_x):
                x0 = self.region_x_edges[kx]
                x1 = self.region_x_edges[kx + 1]
                tf = self.transforms[ky * n_x + kx]
                out[y0:y1, x0:x1] = tf.invert(image[y0:y1, x0:x1])
        return out


def fit_local_intensity_transforms(
    rectified: np.ndarray,
    anchor_pixel_positions: Sequence[tuple[int, int]],
    anchor_patches_true: np.ndarray,
    half_size: int,
    canvas_w: int,
    canvas_h: int,
    n_x: int = 2,
    n_y: int = 2,
) -> LocalIntensityTransformGrid:
    """Fit a separate intensity transform for each of (n_x × n_y) regions
    tiling the canvas.

    Args:
        rectified: (H, W) rectified image in [0, 1].
        anchor_pixel_positions: list of (x, y) pilot center positions.
        anchor_patches_true: (n_pilots, side, side) canonical pilot patches
            (output of select_anchor_codewords).
        half_size: pilot patch half-size.
        canvas_w, canvas_h: canvas dimensions (rectified shape).
        n_x, n_y: number of regions horizontally / vertically.

    Returns:
        LocalIntensityTransformGrid with n_x*n_y transforms.

    Each region's transform is fit on the pilots whose CENTERS fall in
    that region. If a region has zero pilots (degenerate distribution),
    the global transform from all pilots is used as fallback.
    """
    region_x_edges = tuple(int(round(canvas_w * i / n_x)) for i in range(n_x + 1))
    region_y_edges = tuple(int(round(canvas_h * i / n_y)) for i in range(n_y + 1))

    # Bucket pilots into regions
    region_pilots: dict[int, list[int]] = {}
    for pi, (px, py) in enumerate(anchor_pixel_positions):
        kx = max(0, min(n_x - 1, int(np.searchsorted(region_x_edges, px, side='right') - 1)))
        ky = max(0, min(n_y - 1, int(np.searchsorted(region_y_edges, py, side='right') - 1)))
        region_pilots.setdefault(ky * n_x + kx, []).append(pi)

    # Helper: anchor_patches_true can be either a list or a (N, side, side)
    # numpy array. Accept both, materialize to list for index-based slicing.
    if isinstance(anchor_patches_true, np.ndarray):
        all_true_patches = list(anchor_patches_true)
    else:
        all_true_patches = list(anchor_patches_true)

    # Global fit fallback (used if any region is empty)
    I_true_all, I_obs_all = gather_anchor_pixels(
        rectified, list(anchor_pixel_positions), all_true_patches, half_size,
    )
    global_tf = fit_intensity_transform(I_true_all, I_obs_all)

    transforms: list[IntensityTransform] = []
    for ki in range(n_x * n_y):
        pilot_ids = region_pilots.get(ki, [])
        if not pilot_ids:
            transforms.append(global_tf)
            continue
        region_positions = [anchor_pixel_positions[pi] for pi in pilot_ids]
        region_true = [all_true_patches[pi] for pi in pilot_ids]
        try:
            I_true, I_obs = gather_anchor_pixels(
                rectified, region_positions, region_true, half_size,
            )
            transforms.append(fit_intensity_transform(I_true, I_obs))
        except Exception:
            transforms.append(global_tf)

    return LocalIntensityTransformGrid(
        transforms=transforms,
        region_x_edges=region_x_edges,
        region_y_edges=region_y_edges,
        canvas_w=canvas_w,
        canvas_h=canvas_h,
    )
