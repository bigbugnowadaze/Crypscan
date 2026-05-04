"""Finder detection and homography-based rectification for spike-8A.

Pipeline:
    captured image (potentially warped, noisy, off-axis)
      -> Gaussian smooth (suppress payload germ structure)
      -> binary thresholding to find bright/dark blobs
      -> connected-component analysis
      -> filter components by size + intensity to keep finder candidates
      -> identify which candidate is which corner (NW/NE/SW/SE) via
         relative positions + signature distinguishing SE
      -> compute 4-point homography from observed -> canonical
      -> warp inverse to rectify the carrier
      -> crop to canonical dimensions

Corner identification:

  After we have 4 finder candidates, sort them spatially (top-left,
  top-right, bottom-left, bottom-right) using their (x, y) coordinates.
  The "SE" finder uses FINDER_GLYPH_B; the other three use FINDER_GLYPH_A.
  Re-render both glyph patches via the codebook and compute a small
  template-match correlation against the candidate patch in the captured
  image. Whichever candidate best matches FINDER_GLYPH_B's template is
  the SE corner. The other three are then assigned NW/NE/SW by sorted
  position.
"""
from __future__ import annotations
import numpy as np
from scipy.ndimage import gaussian_filter, label as ndi_label
from skimage.measure import regionprops
from skimage.transform import ProjectiveTransform, warp

from basis import OrthoBasis
from codebook import design_codebook
from finders import (
    FINDER_GLYPH_A, FINDER_GLYPH_B, FINDER_AMP, render_finder_patch,
    canonical_finder_positions,
)


def _detect_blob_candidates(image: np.ndarray, smooth_sigma: float = 0.0,
                              threshold: float | None = None,
                              percentile: float = 99.5,
                              min_area: int = 100, max_area: int = 600) -> list[tuple[float, float, float, float]]:
    """Find candidate finder blobs via threshold + connected components.

    Adaptive threshold (per spike-8A's empirical finder/payload separation):
      - When `threshold` is None (default), threshold is set to the
        `percentile`-th percentile of the image. This adapts to global
        photometric drift (gamma, brightness, contrast) so the finder
        detection does NOT need pre-calibration.
      - At default percentile=99.5, ~0.5% of pixels exceed threshold.
        For a 1280x1280 = 1.64M-pixel canvas that's ~8200 pixels, mostly
        from the 4 finders (~240 bright pixels each + scattered payload
        peaks).
      - Connected-component analysis; keep components with area in
        [min_area, max_area].

    Returns (cx, cy, area, mean_intensity) tuples sorted by area descending.
    """
    if smooth_sigma > 0:
        proc = gaussian_filter(image, sigma=smooth_sigma)
    else:
        proc = image
    if threshold is None:
        threshold = float(np.percentile(proc, percentile))
    binary = proc > threshold
    labels, _ = ndi_label(binary)
    candidates = []
    for region in regionprops(labels, intensity_image=proc):
        if region.area < min_area or region.area > max_area:
            continue
        cy, cx = region.centroid
        mean_i = float(region.intensity_mean)
        candidates.append((cx, cy, region.area, mean_i))
    candidates.sort(key=lambda c: -c[2])
    return candidates


def _identify_corners(
    candidates: list[tuple[float, float, float, float]],
    image: np.ndarray,
    template_a: np.ndarray,
    template_b: np.ndarray,
    half_size: int,
) -> dict[str, tuple[float, float]] | None:
    """Identify which 4 candidates correspond to NW/NE/SW/SE.

    Strategy (rotation-tolerant):
      1. Take top 4 candidates by area.
      2. Compute centroid of the 4.
      3. Identify SE = candidate whose patch best matches template_b (the
         asymmetric SE marker glyph). This is rotation-invariant.
      4. Identify NW = candidate diametrically opposite SE (max distance
         from SE through the centroid).
      5. The remaining 2 candidates are NE and SW. Assign by counter-clockwise
         order: starting from the SE -> centroid axis, NE comes BEFORE NW
         (CCW) and SW comes AFTER. Equivalently, the cross product
         sign distinguishes them.

    Returns dict {'NW': (cx, cy), 'NE': ..., 'SW': ..., 'SE': ...} or None
    if 4 candidates can't be confidently identified.
    """
    if len(candidates) < 4:
        return None
    top4 = list(candidates[:4])
    pts = np.array([(c[0], c[1]) for c in top4])
    cx_med = float(np.median(pts[:, 0]))
    cy_med = float(np.median(pts[:, 1]))

    def _patch_at(cx, cy):
        ix = int(round(cx)); iy = int(round(cy))
        x0 = ix - half_size; x1 = ix + half_size + 1
        y0 = iy - half_size; y1 = iy + half_size + 1
        if x0 < 0 or y0 < 0 or x1 > image.shape[1] or y1 > image.shape[0]:
            return None
        return image[y0:y1, x0:x1]

    def _norm(p):
        if p is None:
            return None
        p = p.astype(np.float64) - p.mean()
        n = np.linalg.norm(p)
        return p / n if n > 0 else p

    a_norm = _norm(template_a.astype(np.float64))
    b_norm = _norm(template_b.astype(np.float64))

    def _score_b_minus_a(cx, cy):
        pn = _norm(_patch_at(cx, cy))
        if pn is None or a_norm is None or b_norm is None:
            return -np.inf
        return float(np.sum(pn * b_norm) - np.sum(pn * a_norm))

    scores = [_score_b_minus_a(c[0], c[1]) for c in top4]
    se_idx = int(np.argmax(scores))
    se = top4[se_idx]
    se_cx, se_cy = se[0], se[1]

    # NW: diametrically opposite SE through the centroid (greatest distance from SE)
    others = [c for i, c in enumerate(top4) if i != se_idx]
    others.sort(key=lambda c: -((c[0] - se_cx) ** 2 + (c[1] - se_cy) ** 2))
    nw = others[0]
    remaining = others[1:]
    if len(remaining) != 2:
        return None

    # The SE -> NW axis. NE and SW are perpendicular to this axis.
    # Cross product sign distinguishes which side each is on.
    # SE -> NW vector
    ax, ay = nw[0] - se_cx, nw[1] - se_cy
    # SE -> remaining[i] vectors; cross with SE->NW axis.
    # In image coords (y down): cross(SE->NW, SE->X) = ax*(X.y - SE.y) - ay*(X.x - SE.x)
    # Positive cross = X is "to the right" of SE->NW vector (image-coords-clockwise).
    # In canonical orientation: NE is to the right of SE->NW (clockwise from
    # the SE->NW arrow when looking from SE), SW to the left.
    def _cross(c):
        bx, by = c[0] - se_cx, c[1] - se_cy
        return ax * by - ay * bx

    # In canonical layout (image y-down, SE at +x+y from center, NW opposite):
    #   SE->NW vector ax,ay = (-, -)
    #   SE->NE vector  = (0, -)  -> cross = ax*by - ay*bx = (-)(-) - (-)(0) = + POSITIVE
    #   SE->SW vector  = (-, 0)  -> cross = (-)(0) - (-)(-) = - NEGATIVE
    # So NE has GREATER cross than SW. Robust to image rotations because
    # the SE->NW axis defines the local frame and NE is always to one side.
    crosses = [_cross(c) for c in remaining]
    if crosses[0] > crosses[1]:
        ne, sw = remaining[0], remaining[1]
    else:
        ne, sw = remaining[1], remaining[0]

    return {
        'NW': (nw[0], nw[1]),
        'NE': (ne[0], ne[1]),
        'SW': (sw[0], sw[1]),
        'SE': (se_cx, se_cy),
    }


def detect_finders(
    captured: np.ndarray,
    basis: OrthoBasis,
    codebook_seed: int = 20260504,
    n_codewords: int = 256,
    smooth_sigma: float = 0.0,
    threshold: float | None = None,
    percentile: float = 99.5,
    min_area: int = 100,
    max_area: int = 600,
) -> dict[str, tuple[float, float]] | None:
    """Detect 4 corner finders in a captured image."""
    codebook = design_codebook(basis, n_codewords=n_codewords, seed=codebook_seed)
    template_a = render_finder_patch(FINDER_GLYPH_A, codebook, basis)
    template_b = render_finder_patch(FINDER_GLYPH_B, codebook, basis)
    candidates = _detect_blob_candidates(
        captured, smooth_sigma=smooth_sigma, threshold=threshold,
        percentile=percentile,
        min_area=min_area, max_area=max_area,
    )
    return _identify_corners(candidates, captured, template_a, template_b, basis.half_size)


def estimate_homography(
    observed_corners: dict[str, tuple[float, float]],
    canonical_corners: dict[str, tuple[float, float]],
) -> ProjectiveTransform | None:
    """Fit a homography mapping observed -> canonical."""
    src = np.array([
        observed_corners['NW'], observed_corners['NE'],
        observed_corners['SW'], observed_corners['SE'],
    ], dtype=np.float64)
    dst = np.array([
        canonical_corners['NW'], canonical_corners['NE'],
        canonical_corners['SW'], canonical_corners['SE'],
    ], dtype=np.float64)
    tf = ProjectiveTransform()
    if not tf.estimate(src, dst):
        return None
    return tf


def rectify_carrier(
    captured: np.ndarray,
    canonical_w: int,
    canonical_h: int,
    homography: ProjectiveTransform,
) -> np.ndarray:
    """Warp captured image back to canonical (canonical_h, canonical_w) coords.

    skimage's warp expects an inverse mapping (output -> input). Pass the
    inverse of our (observed -> canonical) homography.
    """
    rectified = warp(
        captured.astype(np.float64),
        homography.inverse,
        output_shape=(canonical_h, canonical_w),
        order=1,
        mode='constant',
        cval=0.5,
        preserve_range=True,
    )
    return rectified.astype(np.float32)
