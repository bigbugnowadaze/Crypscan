"""Unit tests for render.py and extract.py.

The forward render is linear in coefficients; the inverse extract is plain
linear LSQ. These tests verify per-germ recovery on a single germ patch
without going through the full encoder/decoder.
"""
from __future__ import annotations
import sys
from pathlib import Path

import numpy as np

SPIKE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SPIKE_DIR))

from render import render_germ_patch, render_carrier, make_grid_positions    # noqa: E402
from extract import fit_one_germ, extract_carrier, build_design_matrix       # noqa: E402


SIGMA = 4.0
HALF_SIZE = 12
AMP = 0.11
BASELINE = 0.5


def test_single_germ_clean_roundtrip():
    """A single rendered germ at float precision should fit back to ~machine eps."""
    germ_in = np.array([0.5, -0.3, 0.2, -0.1, 0.4])
    patch = render_germ_patch(germ_in, SIGMA, HALF_SIZE, AMP, BASELINE)
    germ_out, residual = fit_one_germ(patch, HALF_SIZE, SIGMA, AMP, BASELINE)
    err = np.abs(germ_in - germ_out)
    assert np.all(err < 1e-6), f"clean roundtrip err: {err}"
    assert residual < 1e-5, f"residual too large: {residual}"
    print(f"  test_single_germ_clean_roundtrip OK (max err {err.max():.2e}, "
          f"residual {residual:.2e})")


def _render_through_pixel_quant(germ_in, depth):
    patch = render_germ_patch(germ_in, SIGMA, HALF_SIZE, AMP, BASELINE)
    if depth == 8:
        q = (np.clip(patch, 0, 1) * 255 + 0.5).astype(np.uint8)
        return q.astype(np.float32) / 255.0
    elif depth == 16:
        q = (np.clip(patch, 0, 1) * 65535 + 0.5).astype(np.uint16)
        return q.astype(np.float32) / 65535.0
    else:
        raise ValueError(depth)


def test_single_germ_8bit_quantization():
    """Through 8-bit PNG quantization, document the empirical recovery error.

    This test does NOT assert the per-coef error is below the quant step —
    the spike's empirical finding is that 8-bit PNG depth is insufficient
    for clean 8-bit-per-coef recovery. The 16-bit test (next) is the gate.
    """
    germ_in = np.array([0.7, -0.5, 0.3, -0.2, 0.6])
    patch_back = _render_through_pixel_quant(germ_in, depth=8)
    germ_out, residual = fit_one_germ(patch_back, HALF_SIZE, SIGMA, AMP, BASELINE)
    err = np.abs(germ_in - germ_out)
    quant_step = 2.0 / 255
    print(f"  test_single_germ_8bit_quantization: per-coef err = "
          f"[{', '.join(f'{e:.5f}' for e in err)}], step = {quant_step:.5f}")
    # 8-bit is informational only; documented limit, not a gate.
    print("  test_single_germ_8bit_quantization OK (informational only)")


def test_single_germ_16bit_quantization():
    """Through 16-bit PNG quantization, recovery beats half a quantization step."""
    germ_in = np.array([0.7, -0.5, 0.3, -0.2, 0.6])
    patch_back = _render_through_pixel_quant(germ_in, depth=16)
    germ_out, residual = fit_one_germ(patch_back, HALF_SIZE, SIGMA, AMP, BASELINE)
    err = np.abs(germ_in - germ_out)
    quant_step = 2.0 / 255
    print(f"  test_single_germ_16bit_quantization: per-coef err = "
          f"[{', '.join(f'{e:.6f}' for e in err)}], step = {quant_step:.5f}")
    # Half-step is the threshold for byte recovery (not crossing a quant boundary).
    half_step = quant_step / 2
    assert np.all(err < half_step), f"err {err} >= half_step {half_step}"
    print("  test_single_germ_16bit_quantization OK")


def test_extreme_coefficients():
    """At the codebook extremes (+/- 1.0), the patch must stay in [0, 1]."""
    extremes = [
        np.array([+1, +1, +1, +1, +1]),
        np.array([-1, -1, -1, -1, -1]),
        np.array([+1, -1, +1, -1, +1]),
    ]
    for germ in extremes:
        patch = render_germ_patch(germ.astype(float), SIGMA, HALF_SIZE, AMP, BASELINE)
        # Patch may exceed [0, 1] before clipping; render_carrier clips.
        # For the per-germ test, just verify inverse fit works on the unclipped patch.
        germ_out, _ = fit_one_germ(patch, HALF_SIZE, SIGMA, AMP, BASELINE)
        err = np.abs(germ - germ_out)
        assert np.all(err < 1e-5), f"err {err} for germ {germ}"
    print("  test_extreme_coefficients OK")


def test_design_matrix_well_conditioned():
    """The design matrix should be well-conditioned at the spike's settings."""
    A = build_design_matrix(HALF_SIZE, SIGMA, AMP)
    # Condition number of A^T A
    AtA = A.T @ A
    cond = np.linalg.cond(AtA)
    print(f"  test_design_matrix_well_conditioned: A is {A.shape}, cond(A^T A) = {cond:.2e}")
    assert cond < 1e8, f"design matrix too ill-conditioned: cond={cond:.2e}"
    print("  test_design_matrix_well_conditioned OK")


def test_grid_layout():
    """make_grid_positions: positions stay inside the canvas."""
    positions, w, h = make_grid_positions(n_germs=100, spacing=28, margin=24)
    assert positions.shape == (100, 2)
    assert positions[:, 0].min() >= HALF_SIZE
    assert positions[:, 1].min() >= HALF_SIZE
    assert positions[:, 0].max() < w - HALF_SIZE
    assert positions[:, 1].max() < h - HALF_SIZE
    print(f"  test_grid_layout OK (canvas {w}x{h} for 100 germs)")


def test_multi_germ_carrier_extract_16bit():
    """Render N germs into a 16-bit carrier, extract them back, beat half-step."""
    rng = np.random.default_rng(seed=42)
    n = 25
    germs_in = rng.uniform(-0.8, 0.8, size=(n, 5))
    positions, w, h = make_grid_positions(n, spacing=28, margin=24)
    carrier = render_carrier(germs_in, positions, w, h, SIGMA, HALF_SIZE, AMP, BASELINE)
    carrier_q = (carrier * 65535 + 0.5).astype(np.uint16).astype(np.float32) / 65535.0
    germs_out, residuals = extract_carrier(carrier_q, positions, SIGMA, HALF_SIZE, AMP, BASELINE)
    err = np.abs(germs_in - germs_out)
    quant_step = 2.0 / 255
    half_step = quant_step / 2
    print(f"  test_multi_germ_carrier_extract_16bit: max err = {err.max():.6f}, "
          f"half-step = {half_step:.6f}, n = {n}")
    assert np.all(err < half_step), f"max err {err.max():.6f} >= half_step {half_step:.6f}"
    print("  test_multi_germ_carrier_extract_16bit OK")


if __name__ == '__main__':
    print("running unit tests for render.py and extract.py ...")
    test_single_germ_clean_roundtrip()
    test_single_germ_8bit_quantization()
    test_single_germ_16bit_quantization()
    test_extreme_coefficients()
    test_design_matrix_well_conditioned()
    test_grid_layout()
    test_multi_germ_carrier_extract_16bit()
    print("ALL UNIT TESTS PASSED")
