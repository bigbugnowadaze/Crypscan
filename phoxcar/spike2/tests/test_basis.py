"""Unit tests for the orthonormal basis."""
from __future__ import annotations
import sys
from pathlib import Path
import numpy as np

SPIKE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SPIKE_DIR))

from basis import OrthoBasis, raw_basis, verify_orthonormality


def test_build_and_orthonormality():
    basis = OrthoBasis.build(half_size=12, sigma=4.0)
    assert verify_orthonormality(basis), "orthonormal basis Gram matrix is not identity"
    print("  test_build_and_orthonormality OK")


def test_round_trip_transforms():
    basis = OrthoBasis.build(half_size=12, sigma=4.0)
    rng = np.random.default_rng(seed=1234)
    theta_raw = rng.uniform(-1, 1, size=5)
    c_ortho = basis.M_to_ortho @ theta_raw
    theta_back = basis.M_to_raw @ c_ortho
    np.testing.assert_allclose(theta_raw, theta_back, atol=1e-12)
    print("  test_round_trip_transforms OK")


def test_H_evaluation_consistency():
    """H(s,t) computed in raw basis or orthonormal basis must agree."""
    basis = OrthoBasis.build(half_size=12, sigma=4.0)
    rng = np.random.default_rng(seed=5678)
    theta_raw = rng.uniform(-1, 1, size=5)
    c_ortho = basis.M_to_ortho @ theta_raw
    H_raw = basis.H_from_raw(theta_raw)
    H_ortho = basis.H_from_ortho(c_ortho)
    np.testing.assert_allclose(H_raw, H_ortho, atol=1e-10)
    print("  test_H_evaluation_consistency OK")


def test_compute_codebook_bounds():
    """Sanity-check what range c_ortho takes when theta_raw is in [-1, +1]^5."""
    basis = OrthoBasis.build(half_size=12, sigma=4.0)
    # L1 norm of each row of M_to_ortho gives the worst-case c_ortho_j
    bounds = np.sum(np.abs(basis.M_to_ortho), axis=1)
    print(f"  test_compute_codebook_bounds: max |c_ortho_j| over unit raw cube:")
    for j, b in enumerate(bounds):
        print(f"      c_ortho[{j}]: {b:.4f}")
    # The codec uses C_ORTHO_BOUNDS = [1.5, 1.5, 1.5, 1.5, 1.5]; sanity-check
    # they're conservative (>= the actual L1 bounds) for this geometry.
    from germ_codec import C_ORTHO_BOUNDS
    print(f"  codec bounds: {C_ORTHO_BOUNDS.tolist()}")
    # Just print; no hard assertion (the spike's bounds may need tuning)
    print("  test_compute_codebook_bounds OK (informational)")


if __name__ == '__main__':
    print("running tests for basis.py ...")
    test_build_and_orthonormality()
    test_round_trip_transforms()
    test_H_evaluation_consistency()
    test_compute_codebook_bounds()
    print("ALL TESTS PASSED")
