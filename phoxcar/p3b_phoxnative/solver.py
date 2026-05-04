"""Linear LSQ inverse fit for spike-3.

Forward model:
    intensity(s, t) = sigmoid(baseline + amp * H(s, t))

Apply logit:
    logit(intensity) = baseline + amp * H(s, t)
    (logit(intensity) - baseline) / amp = H(s, t) = raw_basis(s, t) @ theta_raw

This is plain linear least-squares in theta_raw. Closed-form via
np.linalg.lstsq, weighted by the Gaussian envelope from the orthonormal
basis (which downweights corner pixels where intensity may saturate
near 0 or 1 and the logit becomes noisy).

Numerical care: clip intensity to (eps, 1-eps) before logit to avoid
infinities at the saturation extremes.
"""
from __future__ import annotations
import numpy as np

from basis import OrthoBasis


def fit_one_germ_sigmoid(
    patch: np.ndarray,
    basis: OrthoBasis,
    amp: float,
    baseline: float = 0.0,
    eps_intensity: float = 1e-4,
) -> tuple[np.ndarray, float, dict]:
    """Fit one germ's theta_raw via linear LSQ on logit(I) - baseline = amp * H.

    Args:
        patch: (2*half_size+1, 2*half_size+1) float intensity.
        basis: precomputed OrthoBasis.
        amp, baseline: must match the encoder.
        eps_intensity: clip intensity to (eps, 1-eps) before logit.

    Returns:
        theta_raw: (5,) recovered raw coefficients.
        residual: L2 residual.
        info: dict with diagnostic counts.
    """
    expected_shape = (2 * basis.half_size + 1, 2 * basis.half_size + 1)
    if patch.shape != expected_shape:
        raise ValueError(f"patch shape {patch.shape} != expected {expected_shape}")
    I = patch.ravel().astype(np.float64)
    I_clamped = np.clip(I, eps_intensity, 1.0 - eps_intensity)
    logit_I = np.log(I_clamped / (1.0 - I_clamped))
    target = (logit_I - baseline) / amp                       # = H(s, t) ideally

    # Weight by Gaussian envelope — downweights corner pixels which carry
    # higher logit-noise per unit intensity-noise (sigmoid'(z) is small at
    # extremes, so logit residuals are noisier there). The envelope also
    # downweights pixels far from the germ center where higher-order H
    # terms dominate.
    sqrt_w = np.sqrt(basis.weights)
    A = sqrt_w[:, None] * basis.raw_basis_at_pixels             # (P, 5)
    b = sqrt_w * target                                          # (P,)

    theta, _, _, _ = np.linalg.lstsq(A, b, rcond=None)
    pred = A @ theta
    residual = float(np.linalg.norm(pred - b))
    info = {
        'n_pixels': int(I.size),
        'amp': amp,
        'baseline': baseline,
    }
    return theta, residual, info


def fit_carrier_sigmoid(
    carrier: np.ndarray,
    positions: np.ndarray,
    basis: OrthoBasis,
    amp: float,
    baseline: float = 0.0,
) -> tuple[np.ndarray, np.ndarray]:
    """Run linear LSQ at every known position. Returns (thetas_raw, residuals).

    Pre-factorizes the design matrix once since the geometry is shared.
    """
    sqrt_w = np.sqrt(basis.weights)
    A = sqrt_w[:, None] * basis.raw_basis_at_pixels
    AtA = A.T @ A
    AtA_inv = np.linalg.inv(AtA)
    n = positions.shape[0]
    thetas = np.zeros((n, 5), dtype=np.float64)
    residuals = np.zeros(n, dtype=np.float64)
    H_img, W_img = carrier.shape
    half_size = basis.half_size
    eps = 1e-4
    for i in range(n):
        cx, cy = int(positions[i, 0]), int(positions[i, 1])
        x0 = cx - half_size
        x1 = cx + half_size + 1
        y0 = cy - half_size
        y1 = cy + half_size + 1
        if x0 < 0 or y0 < 0 or x1 > W_img or y1 > H_img:
            raise ValueError(f"germ {i} at ({cx},{cy}) overflows {W_img}x{H_img}")
        patch = carrier[y0:y1, x0:x1].astype(np.float64)
        I = patch.ravel()
        I_clamped = np.clip(I, eps, 1.0 - eps)
        logit_I = np.log(I_clamped / (1.0 - I_clamped))
        target = (logit_I - baseline) / amp
        b = sqrt_w * target
        theta = AtA_inv @ (A.T @ b)
        thetas[i] = theta
        residuals[i] = float(np.linalg.norm(A @ theta - b))
    return thetas, residuals
