"""Nonlinear inverse fit for spike-2.

Forward (CRYPSOID-strict):
    intensity(s, t) = exp(-0.5 * (mahal_sq(s, t) + H(s, t; theta)^2))

Take logs and rearrange:
    -2 * log(intensity) - mahal_sq = H(s, t; theta)^2

The right-hand side is a quadratic-in-theta polynomial. The fit problem
is: given an observed intensity patch and known mahal_sq grid, find
theta minimizing

    sum_pixels w(s, t) * (-2*log(I) - mahal_sq - H(theta)^2)^2

This is a nonlinear least squares problem. We use `scipy.optimize.least_squares`
with Levenberg-Marquardt, warm-started from a linear LSQ on the
*linearized* spike-1 model (which gives a good initial guess in low-noise
regimes).

The H^2 term is sign-symmetric: theta and -theta produce the same
residual. The fit returns one of the two solutions; the codec applies a
sign convention to canonicalize.
"""
from __future__ import annotations
import numpy as np
from scipy.optimize import least_squares

from basis import OrthoBasis


def linear_warm_start(
    patch: np.ndarray,
    basis: OrthoBasis,
    amp_linear: float = 0.11,
    baseline_linear: float = 0.5,
) -> np.ndarray:
    """Spike-1's linear model, used to bootstrap an initial theta_raw guess.

    Spike-1's forward: intensity ~= baseline + amp * exp(-0.5*r^2) * H.
    Inverting: H ~= (intensity - baseline) / (amp * exp(-0.5*r^2)).

    Even though spike-2's actual forward is exp(-0.5*(mahal + H^2)), the
    spike-1 inverse gives a useful initial direction in the cone of
    feasible theta — the LM solver converges in a few iterations from
    here. NOT a substitute for the strict fit; just a warm start.

    Returns theta_raw (5,).
    """
    p = patch.ravel().astype(np.float64) - baseline_linear
    A = amp_linear * basis.weights[:, None] * basis.raw_basis_at_pixels
    theta, _, _, _ = np.linalg.lstsq(A, p, rcond=None)
    return theta


def strict_residuals(theta_raw: np.ndarray, patch_log_target: np.ndarray,
                       fit_weights: np.ndarray, basis: OrthoBasis) -> np.ndarray:
    """The Levenberg-Marquardt residual vector.

    patch_log_target = -2 * log(observed_intensity) - mahal_sq  (target H^2)
    fit_weights      = saturation-aware sqrt-weights per pixel
                       (zero at pixels saturated by 8-bit pixel quantization,
                        sqrt(basis_weights) elsewhere)

    Residual: fit_weights * (patch_log_target - H(theta)^2)
    """
    H = basis.H_from_raw(theta_raw)
    return fit_weights * (patch_log_target - H * H)


def strict_jacobian(theta_raw: np.ndarray, patch_log_target: np.ndarray,
                      fit_weights: np.ndarray, basis: OrthoBasis) -> np.ndarray:
    """Analytic Jacobian of strict_residuals w.r.t. theta_raw.

    d(residual)/d(theta_raw) = -2 * fit_weights * H * d(H)/d(theta)
                              = -2 * fit_weights * H * raw_basis
    """
    H = basis.H_from_raw(theta_raw)
    return (-2.0 * fit_weights * H)[:, None] * basis.raw_basis_at_pixels


def fit_one_germ_strict(
    patch: np.ndarray,
    basis: OrthoBasis,
    saturation_threshold: float = 1.5 / 255.0,
    eps_intensity: float = 1e-9,
) -> tuple[np.ndarray, float, dict]:
    """Fit one germ's theta_raw from a (2*half_size+1)^2 patch via
    Levenberg-Marquardt on the log-space residual.

    `saturation_threshold` masks out pixels whose observed intensity is
    near or below the 8-bit pixel quantization floor (default ~1.5/255).
    Those pixels carry no information about theta beyond "action is large
    here," and the fit's log-space target there would be biased toward
    log(eps_intensity), pulling theta toward smaller magnitudes. Masking
    them recovers correctness in the high-action / low-intensity regime.

    Returns (theta_raw, residual_l2_norm, info_dict).
    """
    expected_shape = (2 * basis.half_size + 1, 2 * basis.half_size + 1)
    if patch.shape != expected_shape:
        raise ValueError(f"patch shape {patch.shape} != expected {expected_shape}")
    I = patch.ravel().astype(np.float64)
    I_clamped = np.clip(I, eps_intensity, 1.0)
    span = np.arange(-basis.half_size, basis.half_size + 1, dtype=np.float64)
    px, py = np.meshgrid(span, span, indexing='xy')
    s = (px / basis.sigma).ravel()
    t = (py / basis.sigma).ravel()
    mahal_sq = s * s + t * t
    log_target = -2.0 * np.log(I_clamped) - mahal_sq

    # Saturation mask: pixels whose intensity is at or below the
    # quantization floor are excluded from the fit. We additionally weight
    # pixels by I — brighter pixels carry more SNR per unit quantization
    # noise, since d(log I)/d(I) = 1/I and the log-target's noise is
    # 2 * pixel_noise / I. So upweighting by I is variance-optimal.
    not_saturated = I > saturation_threshold
    intensity_weight = I_clamped * not_saturated.astype(np.float64)
    sqrt_w = np.sqrt(basis.weights * intensity_weight)
    fit_weights = sqrt_w
    n_active = int(not_saturated.sum())

    # Multi-restart strategy: try both +linear_warm_start and -linear_warm_start
    # (the H^2 model has a sign-symmetric basin structure, but the LM may get
    # stuck in a wrong local minimum from a poor initial guess at high
    # quantization noise). Pick the result with the lower residual.
    theta_lin = linear_warm_start(patch, basis)
    starts = [theta_lin, -theta_lin]

    # Bound theta to the physical codebook (theta_raw_l_inf=1.0 default
    # for the spike). Use trust-region reflective which supports bounds.
    bound = 1.0
    bounds = (np.full(5, -bound), np.full(5, +bound))
    best_result = None
    best_residual = np.inf
    for theta0 in starts:
        # Clip warm start to bounds to avoid trf rejection
        theta0_clipped = np.clip(theta0, -bound, +bound)
        try:
            result = least_squares(
                strict_residuals, theta0_clipped,
                jac=strict_jacobian,
                args=(log_target, fit_weights, basis),
                method='trf',
                bounds=bounds,
                max_nfev=500,
                xtol=1e-12,
                ftol=1e-12,
            )
            r = float(np.linalg.norm(result.fun))
            if r < best_residual:
                best_residual = r
                best_result = result
        except Exception:
            continue
    if best_result is None:
        raise RuntimeError("trf fit failed for all warm starts")
    result = best_result
    theta = result.x.astype(np.float64)
    residual = best_residual
    info = {
        'nfev': int(result.nfev),
        'success': bool(result.success),
        'cost': float(result.cost),
        'n_active_pixels': n_active,
        'n_total_pixels': int(I.size),
    }
    return theta, residual, info


def fit_carrier_strict(
    carrier: np.ndarray,
    positions: np.ndarray,
    basis: OrthoBasis,
) -> tuple[np.ndarray, np.ndarray]:
    """Run the strict nonlinear fit at every known position.

    Returns:
        thetas_raw: (N, 5) recovered raw coefficients (sign-ambiguous up
                    to global flip; codec resolves).
        residuals: (N,) per-germ L2 residual.
    """
    n = positions.shape[0]
    thetas = np.zeros((n, 5), dtype=np.float64)
    residuals = np.zeros(n, dtype=np.float64)
    H, W = carrier.shape
    half_size = basis.half_size
    for i in range(n):
        cx, cy = int(positions[i, 0]), int(positions[i, 1])
        x0 = cx - half_size
        x1 = cx + half_size + 1
        y0 = cy - half_size
        y1 = cy + half_size + 1
        if x0 < 0 or y0 < 0 or x1 > W or y1 > H:
            raise ValueError(f"germ {i} at ({cx},{cy}) overflows {W}x{H}")
        patch = carrier[y0:y1, x0:x1].astype(np.float64)
        theta, residual, _ = fit_one_germ_strict(patch, basis)
        thetas[i] = theta
        residuals[i] = residual
    return thetas, residuals
