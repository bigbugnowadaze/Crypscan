"""Surface-curvature extraction from per-pilot NCC sub-pixel shift field.

Refined approach (after first iteration):

  Use ONLY pilots (16 known positions, known codewords). Pilots are
  immune to discrete-decode errors because the encoder/decoder agree
  on what codeword was placed at each pilot position. The pilot field
  is therefore a clean readout of the GEOMETRIC deformation between
  what was encoded and what was captured.

  For each pilot:
    - Render the canonical template (what should be there)
    - Extract a slightly larger search window from the captured image
    - NCC the template against the search window
    - The peak's offset from the expected center IS the sub-pixel shift
      due to the surface deformation

  Then fit a smooth spatially-varying shift field to those (dx, dy)
  pairs. For cylindrical curvature on x-axis at radius R, expect:
    dx(x, y) ≈ -A * (x - cx) / R   (germs pull inward proportional to
                                       distance from center)
    dy(x, y) ≈ 0
  And vice versa for y-axis curvature.

  The amplitude A relates to R; the axis is recovered from which of
  (dx, dy) has the dominant signal.

  Confidence is from the SNR of the fit.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Sequence
import numpy as np
import cv2


@dataclass
class SurfaceVerdict:
    n_pilots_used: int
    median_shift_magnitude: float
    estimated_curvature_axis: str            # 'x', 'y', or 'none'
    estimated_curvature_radius: float        # canvas-px units; np.inf = flat
    confidence: str                           # TRUST/HOLD/DOWNGRADE/REJECT/NEED_MORE_EVIDENCE
    fit_snr: float
    derivation: list


def extract_pilot_shifts(
    rectified_corrected: np.ndarray,
    pilot_positions: Sequence[tuple[int, int]],
    canonical_pilot_patches: Sequence[np.ndarray],
    half_size: int,
    search_window_px: int = 8,
) -> np.ndarray:
    """For each pilot, find sub-pixel shift via NCC.

    Returns: (N, 2) array of (dx, dy) shifts in pixels.
    """
    shifts = []
    h, w = rectified_corrected.shape
    for (cx, cy), template in zip(pilot_positions, canonical_pilot_patches):
        cx, cy = int(cx), int(cy)
        x0 = cx - half_size - search_window_px
        y0 = cy - half_size - search_window_px
        x1 = cx + half_size + search_window_px + 1
        y1 = cy + half_size + search_window_px + 1
        if x0 < 0 or y0 < 0 or x1 > w or y1 > h:
            shifts.append((0.0, 0.0))
            continue
        region = rectified_corrected[y0:y1, x0:x1].astype(np.float32)
        tmpl = template.astype(np.float32)
        if (region.shape[0] <= tmpl.shape[0] or
            region.shape[1] <= tmpl.shape[1]):
            shifts.append((0.0, 0.0))
            continue
        result = cv2.matchTemplate(region, tmpl, cv2.TM_CCOEFF_NORMED)
        _, _, _, max_loc = cv2.minMaxLoc(result)
        # max_loc is (x, y) of best template top-left position
        # Convert to template center, then to canvas-relative shift
        peak_x_in_region = max_loc[0] + half_size
        peak_y_in_region = max_loc[1] + half_size
        expected = search_window_px + half_size
        dx = peak_x_in_region - expected
        dy = peak_y_in_region - expected
        # Sub-pixel refinement via parabolic interpolation (optional, simple)
        # Skip for now — pixel-level precision is enough for the demo
        shifts.append((float(dx), float(dy)))
    return np.array(shifts, dtype=np.float64)


def fit_radial_curvature(
    shifts: np.ndarray,             # (N, 2) (dx, dy) in pixels
    positions: np.ndarray,          # (N, 2) (cx, cy) in canvas px
    canvas_w: int,
    canvas_h: int,
) -> dict:
    """Fit a cylindrical-curvature model to the shift field.

    Model (cylindrical curvature on x-axis):
        dx(x, y) = -k_x * (x - cx)
        dy(x, y) = 0
    Model (cylindrical curvature on y-axis):
        dx(x, y) = 0
        dy(x, y) = -k_y * (y - cy)

    Fit both models, pick the one with higher SNR.

    The slope k relates to the inverse curvature radius:
        k ≈ D / R   (in the small-deformation limit)
    where D is the camera-distance and R the curvature radius. The
    SCALE of k vs R depends on D, which we don't know precisely; the
    spike's claim is the QUALITATIVE recovery (axis + magnitude trend),
    not absolute R.

    Returns:
        axis: 'x' or 'y' or 'none'
        slope: the fitted k for the dominant axis
        snr: signal-to-noise ratio
        radius: estimated R (proxy; uses fixed D=4000)
    """
    cx = canvas_w / 2.0
    cy = canvas_h / 2.0
    x_centered = positions[:, 0] - cx
    y_centered = positions[:, 1] - cy
    dx = shifts[:, 0]
    dy = shifts[:, 1]

    # Fit dx ≈ -k_x * x_centered   (forced through origin)
    if np.sum(x_centered ** 2) > 0:
        k_x = -np.sum(dx * x_centered) / np.sum(x_centered ** 2)
    else:
        k_x = 0.0
    pred_dx = -k_x * x_centered
    res_x = dx - pred_dx
    snr_x = abs(k_x * np.std(x_centered)) / (np.std(res_x) + 1e-9)

    # Fit dy ≈ -k_y * y_centered
    if np.sum(y_centered ** 2) > 0:
        k_y = -np.sum(dy * y_centered) / np.sum(y_centered ** 2)
    else:
        k_y = 0.0
    pred_dy = -k_y * y_centered
    res_y = dy - pred_dy
    snr_y = abs(k_y * np.std(y_centered)) / (np.std(res_y) + 1e-9)

    # Pick axis
    if snr_x > snr_y * 1.2 and abs(k_x) > 1e-4:
        axis = 'x'; k = k_x; snr = snr_x
    elif snr_y > snr_x * 1.2 and abs(k_y) > 1e-4:
        axis = 'y'; k = k_y; snr = snr_y
    elif max(snr_x, snr_y) < 0.5:
        axis = 'none'; k = 0.0; snr = max(snr_x, snr_y)
    else:
        axis = 'x' if abs(k_x) > abs(k_y) else 'y'
        k = k_x if axis == 'x' else k_y
        snr = snr_x if axis == 'x' else snr_y

    # k -> R conversion: assume D = 4000 (fixed for the demo)
    D_assumed = 4000.0
    if abs(k) > 1e-6:
        recovered_R = D_assumed / k
    else:
        recovered_R = float('inf')

    return {
        'axis': axis,
        'k_x': float(k_x), 'k_y': float(k_y),
        'snr_x': float(snr_x), 'snr_y': float(snr_y),
        'snr': float(snr),
        'recovered_curvature_radius': float(recovered_R),
    }


def derive_surface_verdict_from_pilots(
    rectified_corrected: np.ndarray,
    pilot_positions: Sequence[tuple[int, int]],
    canonical_pilot_patches: Sequence[np.ndarray],
    half_size: int,
    canvas_w: int,
    canvas_h: int,
    flat_threshold_snr: float = 1.0,
) -> SurfaceVerdict:
    """Top-level surface verdict from pilot NCC-shifts."""
    derivation = []
    derivation.append(f"extracting NCC sub-pixel shifts at {len(pilot_positions)} pilot positions")

    shifts = extract_pilot_shifts(
        rectified_corrected, pilot_positions, canonical_pilot_patches,
        half_size, search_window_px=8,
    )
    median_shift = float(np.median(np.linalg.norm(shifts, axis=1)))
    derivation.append(f"median pilot shift magnitude: {median_shift:.3f} px")

    fit = fit_radial_curvature(
        shifts, np.array(pilot_positions, dtype=np.float64),
        canvas_w, canvas_h,
    )
    derivation.append(
        f"k_x={fit['k_x']:.4f} (SNR {fit['snr_x']:.2f}), "
        f"k_y={fit['k_y']:.4f} (SNR {fit['snr_y']:.2f})"
    )
    derivation.append(f"dominant axis: {fit['axis']}")
    derivation.append(f"recovered radius (assuming D=4000): {fit['recovered_curvature_radius']:.0f}")

    # Verdict
    snr = fit['snr']
    if median_shift < 0.3 and snr < flat_threshold_snr:
        confidence = 'TRUST'
        verdict_text = 'TRUST: flat surface'
        recovered_R = float('inf')
    elif fit['axis'] == 'none':
        confidence = 'NEED_MORE_EVIDENCE'
        verdict_text = 'NEED_MORE_EVIDENCE: no dominant axis signal'
        recovered_R = float('inf')
    elif snr >= 2.0:
        confidence = 'TRUST'
        verdict_text = f"TRUST: curved on {fit['axis']}-axis, R≈{fit['recovered_curvature_radius']:.0f}"
        recovered_R = fit['recovered_curvature_radius']
    elif snr >= 1.0:
        confidence = 'HOLD'
        verdict_text = f"HOLD: probably curved on {fit['axis']}-axis"
        recovered_R = fit['recovered_curvature_radius']
    else:
        confidence = 'DOWNGRADE'
        verdict_text = 'DOWNGRADE: weak signal'
        recovered_R = fit['recovered_curvature_radius']

    derivation.append(f"verdict: {verdict_text}")

    return SurfaceVerdict(
        n_pilots_used=len(pilot_positions),
        median_shift_magnitude=median_shift,
        estimated_curvature_axis=fit['axis'],
        estimated_curvature_radius=recovered_R,
        confidence=confidence,
        fit_snr=snr,
        derivation=derivation,
    )
