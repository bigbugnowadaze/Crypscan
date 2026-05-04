# phoxcar/p3b_phoxnative — phoxoidal-native pose recovery

**Status:** complete; phoxoidal-native pose recovery feasibility validated
**Authored:** 2026-05-04 (after PR #11 / P3.A)
**Goal:** prove the catastrophe-germ basis can do its OWN pose recovery
without conventional CV (ArUco/AprilTag), opening a research path to
retire the hybrid substrate identity acknowledged in
`phoxoidal_carrier_proposal/ADDENDUM_02_hybrid_identity.md`.

## What P3.B is

The **phoxoidal-native research path** — using catastrophe-germ matched
filters as the pose layer instead of ArUco. The substrate is fully
thesis-aligned end-to-end:

  - encoder renders phoxoidal corner clusters at corners (extremal
    raw-coefficient germs, 3x3 cluster, amp=1.0)
  - decoder runs NCC matched-filter detection against the same germ
    templates the encoder used
  - 4-point homography from observed cluster centers to canonical
    canvas; rectify; spike-7 substrate from there

## Headline result

| Test | Outcome |
|---|---|
| Zero-warp gate | **PASS** (NCC ≈ 1.0 on all 4 corners) |
| Photometric envelope | **FULL PASS** — matches P3.A / spike-7 across all severities |
| In-frame geometric warps (small) | **PASS** — translation, scale 0.7-1.0, shear ≤5°, tilt ≤10°, sub-pixel |
| Rotation > 5° | **FAIL** by design — saddle/trefoil rotational symmetries (fixable) |
| Rolling shutter | **FAIL** by design — NCC rigid-template vs row-wise shear |
| Extreme tilt / off-canvas | **FAIL** — same as P3.A (synthetic-test artifact) |

**The catastrophe-germ basis CAN do its own pose recovery.** The
phoxoidal-native path is feasible. The pose-layer geometric envelope is
narrower than ArUco's at extreme orientations but matches in-frame and
**fully matches the photometric envelope**.

See `results/P3B_REPORT.md` for the full sweep + per-axis pass/fail.

## Why this matters

`ADDENDUM_02_hybrid_identity.md` acknowledged that P3.A's pose layer is
conventional CV (ArUco), not catastrophe-germ-native. P3.B answers the
implicit question: **does the thesis HAVE to defer to conventional CV
for pose, or can it carry that layer too?**

The answer: it can carry that layer, with a known and addressable gap
on rotation/rolling-shutter that P3.C iterations would close.

## Files

| File | Purpose |
|---|---|
| `header.py`, `basis.py`, `density.py`, `solver.py`, `germ_codec.py`, `ecc.py`, `codebook.py`, `pilots.py`, `noise.py`, `manifest.py`, `geometric_noise.py` | reused verbatim from P3.A (frozen substrate layers 1-4 + 6-8) |
| `fiducials.py` | phoxoidal corner cluster design |
| `pose.py` | NCC matched-filter pose recovery |
| `encoder.py`, `decoder.py` | sidecar-free, fully phoxoidal-native pipeline |
| `test_zero_warp.py` | smoke test |
| `test_acceptance_gate.py` | full sweep (matches P3.A's gate) |
| `results/P3B_REPORT.md` | full report |

## Reproduce

```bash
pip install brotli reedsolo numpy scipy Pillow scikit-image opencv-python
cd phoxcar/p3b_phoxnative
python3 test_zero_warp.py        # ~3s
python3 test_acceptance_gate.py  # ~100s
```
