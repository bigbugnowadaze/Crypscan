"""Orthonormal 5-coefficient germ basis under Gaussian-weighted patch inner product.

The raw CRYPSOID basis (`tools/crypsorender/math/germ.py` lines 23-30):

    B_0(s, t) = s^2
    B_1(s, t) = t^2
    B_2(s, t) = s^3 - 3 s t^2
    B_3(s, t) = 3 s^2 t - t^3
    B_4(s, t) = s^4 + t^4

is NOT orthogonal under the inner product

    <f, g> = sum_pixels  exp(-0.5 * (s^2 + t^2)) * f(s, t) * g(s, t)

over the spike's patch. Cross-terms like <B_0, B_4> = <s^2, s^4 + t^4> are
non-zero. So a noise event in the inverse fit gets coupled across
coefficients.

This module computes a Cholesky-orthogonalized basis spanning the SAME
5-D function space, with the property that

    <B_ortho_i, B_ortho_j>_w = delta_ij

So independent noise per orthonormal coordinate.

Conversion:
    theta_raw    = M_to_raw    @ c_ortho
    c_ortho      = M_to_ortho  @ theta_raw

The orthonormal basis is greedy (Gram-Schmidt-equivalent), so c_ortho[0]
is the projection onto the normalized first raw basis function (s^2),
c_ortho[1] is the residual along (t^2 - <t^2, B_ortho_0>), etc. This
ordering matters for the sign convention in the codec — see codec.py.
"""
from __future__ import annotations
from dataclasses import dataclass
import numpy as np


def raw_basis(s: np.ndarray, t: np.ndarray) -> np.ndarray:
    """Stack the 5 raw basis functions [s^2, t^2, s^3-3st^2, 3s^2t-t^3, s^4+t^4].

    Returns array of shape s.shape + (5,).
    """
    s2 = s * s
    t2 = t * t
    return np.stack([
        s2,
        t2,
        s * s2 - 3.0 * s * t2,
        3.0 * s2 * t - t * t2,
        s2 * s2 + t2 * t2,
    ], axis=-1)


def gaussian_weights(half_size: int, sigma: float) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Return (s, t, w) flat arrays for the patch."""
    span = np.arange(-half_size, half_size + 1, dtype=np.float64)
    px, py = np.meshgrid(span, span, indexing='xy')
    s = (px / sigma).ravel()
    t = (py / sigma).ravel()
    w = np.exp(-0.5 * (s * s + t * t))
    return s, t, w


@dataclass
class OrthoBasis:
    """Cached orthonormal basis for a fixed (half_size, sigma) patch."""
    half_size: int
    sigma: float
    M_to_raw: np.ndarray      # (5, 5) maps c_ortho -> theta_raw
    M_to_ortho: np.ndarray    # (5, 5) maps theta_raw -> c_ortho
    raw_basis_at_pixels: np.ndarray   # (P, 5) raw basis evaluated at every patch pixel
    ortho_basis_at_pixels: np.ndarray # (P, 5) orthonormal basis at every patch pixel
    weights: np.ndarray       # (P,) per-pixel Gaussian weights
    codebook_bounds: np.ndarray  # (5,) max |c_ortho_j| * margin for codec quantization

    @classmethod
    def build(cls, half_size: int, sigma: float, theta_raw_l_inf: float = 1.0,
              codebook_margin: float = 1.10) -> 'OrthoBasis':
        """Construct the orthonormal basis for the given patch geometry.

        Args:
            half_size, sigma: patch geometry.
            theta_raw_l_inf: L_inf bound assumed on theta_raw (raw codebook
                coefficients). The c_ortho codebook bounds are derived from
                this via the L1 norm of M_to_ortho rows.
            codebook_margin: safety factor on the c_ortho bounds (1.10 = 10%
                margin so quantization edge cases don't clip).
        """
        s, t, w = gaussian_weights(half_size, sigma)
        B_raw = raw_basis(s, t).reshape(-1, 5)              # (P, 5)
        sqrt_w = np.sqrt(w)
        Bw = sqrt_w[:, None] * B_raw                         # (P, 5)
        G = Bw.T @ Bw                                        # (5, 5)
        L = np.linalg.cholesky(G)
        M_to_ortho = L.T
        M_to_raw = np.linalg.inv(M_to_ortho)
        B_ortho = B_raw @ M_to_raw                           # (P, 5)
        # Codebook bounds: pick c_ortho box such that ALL byte patterns
        # decode to theta_raw in [-theta_raw_l_inf, +theta_raw_l_inf]^5.
        # Sufficient condition: |c_ortho|_inf <= theta_raw_l_inf / ||M_to_raw||_inf
        # where ||·||_inf is the operator infinity norm (max row sum of |.|).
        #
        # This is conservative — some byte patterns at the corner of the
        # c_ortho box still produce theta_raw INSIDE the unit cube, so we
        # could pack more germs by quantizing in a parallelepiped. For the
        # spike, the box approximation is adequate.
        op_inf_norm = float(np.max(np.sum(np.abs(M_to_raw), axis=1)))
        bound = theta_raw_l_inf / op_inf_norm / codebook_margin
        codebook_bounds = np.full(5, bound, dtype=np.float64)
        return cls(
            half_size=half_size, sigma=sigma,
            M_to_raw=M_to_raw, M_to_ortho=M_to_ortho,
            raw_basis_at_pixels=B_raw,
            ortho_basis_at_pixels=B_ortho,
            weights=w,
            codebook_bounds=codebook_bounds,
        )

    def H_from_raw(self, theta_raw: np.ndarray) -> np.ndarray:
        """Evaluate H(s, t) at every patch pixel given raw coefficients."""
        return self.raw_basis_at_pixels @ theta_raw

    def H_from_ortho(self, c_ortho: np.ndarray) -> np.ndarray:
        """Evaluate H(s, t) at every patch pixel given orthonormal coefficients."""
        return self.ortho_basis_at_pixels @ c_ortho


def verify_orthonormality(basis: OrthoBasis, atol: float = 1e-10) -> bool:
    """The weighted Gram matrix in orthonormal coords should be the identity."""
    sqrt_w = np.sqrt(basis.weights)
    Bow = sqrt_w[:, None] * basis.ortho_basis_at_pixels
    G_ortho = Bow.T @ Bow
    return np.allclose(G_ortho, np.eye(5), atol=atol)
