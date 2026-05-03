# phoxcar/spike2 — CRYPSOID-faithful Phase 0.5 spike

**Status:** in-progress
**Authorized:** 2026-05-03 (Bug)
**Predecessor:** `../spike/` (linearized model; passes gate at 16-bit, fails at 8-bit)
**Goal:** validate the proposed phoxoidal-carrier symbol-decode pathway using CRYPSOID's *actual* density evaluator at 8-bit pixel depth.

This spike replaces spike-1's spike-speed simplifications with the production-aligned model:

| Layer | spike-1 | spike-2 |
|---|---|---|
| Forward density | `baseline + amp · envelope · H(s,t)` (linear in coefs, sign-preserving) | `exp(-0.5 · (mahal_sq + H(s,t)²))` (CRYPSOID's `phoxoidal_density_germ_full`, `germ.py` lines 194-232) |
| Coefficient basis | Raw 5-coef `[s², t², s³-3st², 3s²t-t³, s⁴+t⁴]` | Same span, orthonormalized under the Gaussian-weighted inner product over the patch |
| Inverse | Linear LSQ | Nonlinear (Levenberg-Marquardt in log-space; quadratic in θ) |
| Sign of H | Preserved by linear model | H² loses sign; recovered by encoder-side sign convention `H(s_ref, t_ref) ≥ 0` |
| Byte-stream ECC | None (R=1) | Reed-Solomon RS(255, 223) — single-byte-flip recovery, ~14% overhead |
| Pixel bit depth | 16 (passes), 8 (fails) | **Target: 8.** 16 is a fallback if 8 still fails. |

## Rationale (Bug, 2026-05-03)

> CRYPSOID purposely avoids gaussian in exchange for semio physics catastrophe theory and the 7 elementary catastrophes to create a new approach. Is that relevant? If we're using crypsoid I assume so right?

Yes. CRYPSOID's thesis is that Gaussians are the boring degenerate case (`docs/thesis_digest.md` line 11) and the catastrophe-germ structure is the substantive carrier. The Gaussian envelope is just spatial localization (the same role it plays in any localized basis). Spike-1 used a linearized `intensity = baseline + amp · envelope · H` to make the inverse fit trivially linear — that was a spike-speed shortcut, not a substrate-faithful choice. Spike-2 uses CRYPSOID's strict `H²` evaluator.

## Pass criteria (same gate as spike-1, run at 8-bit)

1. SHA-256 roundtrip on a ~1000-germ payload.
2. Per-coefficient RMSE in the orthonormalized basis ≤ half quantization step.
3. Total wall time < 60 s (relaxed from spike-1's 30 s budget because nonlinear fit is slower than linear LSQ).
4. **Decision rule:** if 8-bit passes, the substrate is production-target-aligned and Phase 1 P3 has empirical wind. If 8-bit fails, document the empirical limit precisely and recommend Phase 1 strategy (mitigations menu in `../spike/results/SPIKE_REPORT.md` §5.1).

## Honest scope (same as spike-1; nothing added)

Out of scope: noise tolerance, captured-image robustness, manifest cluster bootstrap, Tier C interference, density at production scale. Phase 1 deliverables.

## Files

| File | Purpose |
|---|---|
| `basis.py` | Orthonormal basis on the patch under Gaussian-weighted inner product |
| `density.py` | CRYPSOID-faithful forward density `exp(-0.5·(mahal+H²))` |
| `solver.py` | Nonlinear inverse fit: Levenberg-Marquardt in log-space |
| `germ_codec.py` | Same 8-bits-per-coef quantization as spike-1, but quantization is in the *orthonormal* basis |
| `header.py` | AXP6-equivalent inner header (verbatim from spike-1) |
| `ecc.py` | Reed-Solomon RS(255, 223) byte-stream ECC |
| `encoder.py`, `decoder.py` | End-to-end drivers |
| `test_roundtrip.py` | The 8-bit gate |
| `tests/` | Unit tests for each module |
| `results/SPIKE2_REPORT.md` | Final report (created by the gate run) |

## How to run

```bash
cd phoxcar/spike2
python3 tests/test_basis.py
python3 tests/test_density_and_solver.py
python3 tests/test_codec.py
python3 tests/test_ecc.py
python3 test_roundtrip.py --bit-depth 8
```
