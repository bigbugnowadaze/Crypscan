"""Inverse 5-coefficient germ fit at known positions.

Given the synthetic forward model (see render.py):

    intensity(s, t) = baseline + amp * exp(-0.5 * (s**2 + t**2)) * H(s, t)

with s, t = local sigma-normalized pixel offsets, the residual

    f(s, t) = intensity(s, t) - baseline

is a linear function of the germ coefficients:

    f(s, t) = amp * exp(-0.5 * r**2) * (M(s, t) @ theta)

where M(s, t) = [s^2, t^2, s^3-3st^2, 3s^2t-t^3, s^4+t^4] and
theta = (k1, k2, chi, omega, zeta). So fitting theta is plain linear
least-squares: minimize ||A @ theta - b||^2 with A = amp*g(s,t)*M(s,t)
and b = f(s, t).

Why this works at zero capture noise:
  - Encoder positions and sigma are shared with the decoder (no
    bootstrap problem; that's Phase 1).
  - The forward model's quantization-to-PNG noise is < ~1/255 per pixel.
  - With ~ (2*half_size+1)^2 pixels of independent observations and a
    5-parameter linear fit, the LSQ solution is well-conditioned and the
    per-coefficient RMSE is bounded by the PNG quantization step.
"""
from __future__ import annotations
import numpy as np

from render import germ_basis


def build_design_matrix(
    half_size: int, sigma: float, amp: float
) -> np.ndarray:
    """Build the (P, 5) design matrix A for one germ patch.

    P = (2*half_size+1)^2 is the number of pixels in the patch.
    A[p, j] = amp * exp(-0.5 * r_p^2) * M_j(s_p, t_p).
    """
    span = np.arange(-half_size, half_size + 1, dtype=np.float64)
    px, py = np.meshgrid(span, span, indexing='xy')
    s = (px / sigma).ravel()
    t = (py / sigma).ravel()
    envelope = np.exp(-0.5 * (s * s + t * t))
    M = germ_basis(s, t)                              # (P, 5)
    return amp * envelope[:, None] * M


def fit_one_germ(
    patch: np.ndarray,
    half_size: int,
    sigma: float,
    amp: float,
    baseline: float = 0.5,
) -> tuple[np.ndarray, float]:
    """Fit one germ's 5 coefficients from a (2*half_size+1)^2 patch.

    Returns:
        theta: (5,) recovered coefficients.
        residual: float L2 residual from the LSQ solve.
    """
    expected_shape = (2 * half_size + 1, 2 * half_size + 1)
    if patch.shape != expected_shape:
        raise ValueError(f"patch shape {patch.shape} != expected {expected_shape}")
    A = build_design_matrix(half_size, sigma, amp)
    b = (patch.astype(np.float64) - baseline).ravel()
    theta, _, _, _ = np.linalg.lstsq(A, b, rcond=None)
    pred = A @ theta
    residual = float(np.linalg.norm(pred - b))
    return theta, residual


def extract_carrier(
    carrier: np.ndarray,
    positions: np.ndarray,
    sigma: float,
    half_size: int,
    amp: float,
    baseline: float = 0.5,
) -> tuple[np.ndarray, np.ndarray]:
    """Run the inverse fit at every known position.

    Args:
        carrier: (H, W) float32 image.
        positions: (N, 2) integer pixel centers.
        sigma, half_size, amp, baseline: must match the encoder's settings.

    Returns:
        germs: (N, 5) recovered coefficients.
        residuals: (N,) per-germ L2 residual.
    """
    A = build_design_matrix(half_size, sigma, amp)
    # Pre-factorize once for speed (same A for every germ since we use a
    # global sigma + half_size + amp). LSQ via normal equations because A is
    # tall (P >> 5) and well-conditioned at the scales used here.
    AtA = A.T @ A
    AtA_inv = np.linalg.inv(AtA)
    n = positions.shape[0]
    germs = np.zeros((n, 5), dtype=np.float64)
    residuals = np.zeros(n, dtype=np.float64)
    H, W = carrier.shape
    for i in range(n):
        cx, cy = int(positions[i, 0]), int(positions[i, 1])
        x0 = cx - half_size
        x1 = cx + half_size + 1
        y0 = cy - half_size
        y1 = cy + half_size + 1
        if x0 < 0 or y0 < 0 or x1 > W or y1 > H:
            raise ValueError(f"germ {i} at ({cx},{cy}) overflows {W}x{H}")
        patch = carrier[y0:y1, x0:x1].astype(np.float64)
        b = (patch - baseline).ravel()
        theta = AtA_inv @ (A.T @ b)
        germs[i] = theta
        residuals[i] = float(np.linalg.norm(A @ theta - b))
    return germs, residuals
