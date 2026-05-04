"""Calibration pilots for spike-7.

ChatGPT's spike-7 specification (Bug-audited 2026-05-04): place known
anchor codewords at known scene positions so the decoder can fit
gamma/brightness/contrast and inverse-correct the captured image
*before* running the standard codebook nearest-neighbor decode.

# Why this is needed

Spike-6 took the substrate from "essentially zero-margin" to
"calibration-drift-limited." The remaining failures (gamma drift,
brightness drift > 0.02, contrast drift > 0.18) are *correlated*
intensity remappings, not random noise. ECC + codebook nearest-neighbor
match cannot recover from correlated bias because the same wrong glyph
gets confidently chosen everywhere.

# Approach

The decoder reads the captured image at known anchor positions, knows
what those patches *should* look like (because it knows which codewords
were placed there), and fits a 3-parameter intensity transform:

    I_observed = a + b * I_true^gamma

via nonlinear LSQ over the anchor pixels. Then applies the inverse
transform to every pixel of the captured carrier before running the
spike-6 LSQ + nearest-neighbor pipeline.

# Anchor placement

This module selects 4 anchor codewords from the 256-glyph codebook
that collectively span the [0, 1] intensity range. Encoder reserves
N positions in the grid (typically the corners + mid-edges) for the
anchors. Decoder reads them and fits the transform.

In production these anchor positions would live in a structural
manifest cluster (spike-8 work). For spike-7, we put them in the
sidecar manifest alongside payload-germ positions.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Optional
import numpy as np

from basis import OrthoBasis
from density import render_germ_patch_sigmoid
from codebook import design_codebook


def select_anchor_codewords(
    codebook: np.ndarray,
    basis: OrthoBasis,
    amp: float,
    baseline: float,
    n_anchors: int = 4,
) -> tuple[list[int], list[np.ndarray]]:
    """Pick `n_anchors` codebook indices whose rendered patches collectively
    span the [0, 1] intensity range well.

    Strategy: render every codeword once, compute its (min, max, mean)
    intensity, then greedily pick anchors that fill different bins of
    the intensity range.

    Returns:
        anchor_indices: codeword indices chosen as anchors.
        anchor_patches: rendered (size, size) intensity patches for each
                         anchor (used to know I_true at every patch pixel).
    """
    n_cw = codebook.shape[0]
    intensities = np.zeros((n_cw, 3))   # (min, max, mean) per codeword
    patches = []
    for i in range(n_cw):
        theta_raw = basis.M_to_raw @ codebook[i]
        patch = render_germ_patch_sigmoid(theta_raw, basis, amp, baseline)
        patches.append(patch)
        intensities[i] = [patch.min(), patch.max(), patch.mean()]

    # Greedy farthest-point selection in (mean, range) space to span dynamic range
    means = intensities[:, 2]
    # Pick the codeword with min mean (darkest)
    chosen = [int(np.argmin(means))]
    # Pick the codeword with max mean (brightest)
    chosen.append(int(np.argmax(means)))
    # Greedily fill: pick the codeword whose mean is farthest from already-chosen means
    while len(chosen) < n_anchors:
        chosen_means = means[chosen]
        d = np.min(np.abs(means[:, None] - chosen_means[None, :]), axis=1)
        d[chosen] = -1.0
        chosen.append(int(np.argmax(d)))

    anchor_patches = [patches[i] for i in chosen]
    return chosen, anchor_patches


@dataclass
class IntensityTransform:
    """Parametric intensity transform: I_observed = a + b * I_true^gamma."""
    a: float
    b: float
    gamma: float
    fit_residual: float

    def to_dict(self) -> dict:
        return {
            'a': float(self.a), 'b': float(self.b), 'gamma': float(self.gamma),
            'fit_residual': float(self.fit_residual),
        }

    def apply(self, I_true: np.ndarray) -> np.ndarray:
        """Forward direction: I_observed = a + b * I_true^gamma."""
        I = np.clip(I_true, 1e-6, 1.0 - 1e-6)
        return np.clip(self.a + self.b * np.power(I, self.gamma), 0.0, 1.0)

    def invert(self, I_observed: np.ndarray) -> np.ndarray:
        """Inverse direction: I_true_recovered = ((I_observed - a) / b)^(1/gamma)."""
        z = (I_observed - self.a) / self.b
        z = np.clip(z, 1e-6, 1.0 - 1e-6)
        return np.clip(np.power(z, 1.0 / self.gamma), 0.0, 1.0)


def fit_intensity_transform(
    I_true: np.ndarray,
    I_observed: np.ndarray,
) -> IntensityTransform:
    """Fit `I_observed = a + b * I_true^gamma` via nonlinear LSQ.

    Args:
        I_true: (N,) flat array of expected intensities.
        I_observed: (N,) flat array of observed intensities.

    Returns:
        IntensityTransform with fitted (a, b, gamma).
    """
    from scipy.optimize import least_squares

    I_true = np.clip(np.asarray(I_true, dtype=np.float64).ravel(), 1e-6, 1.0 - 1e-6)
    I_observed = np.asarray(I_observed, dtype=np.float64).ravel()

    def residual(params):
        a, b, gamma = params
        pred = a + b * np.power(I_true, gamma)
        return pred - I_observed

    # Initial guess: identity transform
    x0 = np.array([0.0, 1.0, 1.0])
    bounds = ([-0.5, 0.3, 0.2], [0.5, 3.0, 5.0])
    try:
        result = least_squares(residual, x0, bounds=bounds, max_nfev=200)
        a, b, gamma = result.x
        residual_norm = float(np.linalg.norm(result.fun))
    except Exception:
        a, b, gamma = 0.0, 1.0, 1.0
        residual_norm = float('inf')

    return IntensityTransform(a=a, b=b, gamma=gamma, fit_residual=residual_norm)


def gather_anchor_pixels(
    carrier: np.ndarray,
    anchor_positions: list[tuple[int, int]],
    anchor_patches_true: list[np.ndarray],
    half_size: int,
) -> tuple[np.ndarray, np.ndarray]:
    """Extract (I_true, I_observed) sample pairs from anchor positions.

    Args:
        carrier: (H, W) observed image in [0, 1].
        anchor_positions: list of (cx, cy) pixel coordinates where anchors live.
        anchor_patches_true: list of (size, size) expected I_true patches.
        half_size: patch half-window.

    Returns:
        I_true_flat, I_observed_flat — both 1-D arrays of length
        N_anchors * (2*half_size+1)^2.
    """
    if len(anchor_positions) != len(anchor_patches_true):
        raise ValueError("position and patch lists must align")
    H, W = carrier.shape
    side = 2 * half_size + 1
    Is_true = []
    Is_obs = []
    for (cx, cy), patch_true in zip(anchor_positions, anchor_patches_true):
        x0 = cx - half_size
        x1 = cx + half_size + 1
        y0 = cy - half_size
        y1 = cy + half_size + 1
        if x0 < 0 or y0 < 0 or x1 > W or y1 > H:
            raise ValueError(f"anchor at ({cx},{cy}) overflows {W}x{H}")
        Is_true.append(patch_true.ravel())
        Is_obs.append(carrier[y0:y1, x0:x1].astype(np.float64).ravel())
    return np.concatenate(Is_true), np.concatenate(Is_obs)
