# phoxcar/spike3 — display-optimized phoxoidal carrier

**Status:** in-progress
**Authorized:** 2026-05-03 (Bug)
**Predecessors:** `../spike/` (linear); `../spike2/` (CRYPSOID-faithful strict H²)
**Goal:** ChatGPT's Choice 3 — keep the catastrophe germs, change the visible carrier model. Validate that an 8-bit-friendly **sigmoid display function** (option 1) preserves the 5-coefficient catastrophe-germ thesis while passing the SHA-256 gate at 8-bit pixel depth.

This is the **renderer/carrier separation** thesis:
- CRYPSOID's strict `exp(−0.5·(mahal + H²))` density evaluator stays the truth model for 3DGS scene rendering.
- The phoxoidal **carrier** uses a different display function, optimized for 8-bit visibility, while encoding the same 5-coefficient germs (κ₁/κ₂/χ/ω/ζ) from `tools/crypsorender/math/germ.py`.

## The carrier display function

```
intensity(s, t) = sigmoid(baseline + amp · H(s, t))
H(s, t) = κ₁s² + κ₂t² + χ(s³ − 3st²) + ω(3s²t − t³) + ζ(s⁴ + t⁴)
```

Same Pearcey-class basis CRYPSOID uses for catastrophe-germ classification. The visualization changes; the math doesn't.

### Why this beats spike-2's strict H² for an 8-bit carrier

| Property | spike-2 (`exp(−0.5·(mahal + H²))`) | spike-3 (`sigmoid(baseline + amp · H)`) |
|---|---|---|
| Sign of H | Lost (H is squared) — costs 1 bit per germ to canonical sign convention | Preserved — full 40 bits per germ |
| Inverse fit | Nonlinear (Levenberg-Marquardt) | Linear LSQ in logit space |
| Saturation | Patch corners drop below 8-bit floor at moderate θ | Sigmoid bounded; with `amp` tuned, intensity stays in (0.01, 0.99) |
| Local minima | Yes — H² creates ambiguous basins | No — convex objective |
| Wall time per germ | ~6 ms (LM trust-region) | ~10× faster (linear LSQ) |
| 8-bit gate | FAIL (Brotli error after RS overflow) | **target: PASS** |

### What's preserved from CRYPSOID

- The 5-coefficient Pearcey-class basis verbatim (`tools/crypsorender/math/germ.py` lines 23-30).
- The Cholesky-orthonormalized coordinate system from spike-2 (`basis.py`, reused).
- All physical interpretation: κ₁, κ₂ are curvature; χ, ω are Pearcey cusp generators; ζ is the swallowtail unfolding term.

### What's changed from spike-2

- **Forward density**: sigmoid instead of strict-H² exp.
- **Solver**: linear LSQ instead of Levenberg-Marquardt.
- **Codec**: full 40 bits per germ (no sign convention overhead).

## Inverse fit

Apply logit to both sides:
```
logit(intensity) = baseline + amp · H(s, t)
(logit(intensity) − baseline) / amp = H(s, t) = raw_basis(s, t) · θ
```

The fit is plain linear least-squares: minimize ‖A · θ − b‖² where
- `A[p, j] = sqrt(weight[p]) · raw_basis_at_pixels[p, j]`
- `b[p]   = sqrt(weight[p]) · (logit(I[p]) − baseline) / amp`

Closed-form solution via `np.linalg.lstsq`. Same pattern as spike-1.

## Codec

40 bits per germ, 5 bytes per germ, byte-aligned (no fractional bit packing):

| Byte | Bits | Coefficient |
|---|---|---|
| 0 | 8 | c_ortho[0] index in [0, 255] over [-bound, +bound] |
| 1 | 8 | c_ortho[1] |
| 2 | 8 | c_ortho[2] |
| 3 | 8 | c_ortho[3] |
| 4 | 8 | c_ortho[4] |

No sign convention, no canonicalization. Spike-3 recovers the full 40 bits/germ density.

## Acceptance criterion

**Gate 1 — SHA-256 roundtrip on a ~1000-germ payload at 8-bit pixel depth.** Predicted PASS based on the spike-2 noise analysis; the sigmoid model has cleaner SNR per coefficient than strict H².

**Gate 2 — wall time < 10 s** (relaxed from spike-1's 30 s but tighter than spike-2's 60 s, since linear LSQ is fast).

## Files

| File | Origin |
|---|---|
| `basis.py` | reused from spike-2 (Cholesky orthonormal basis) |
| `header.py` | reused from spike-1/spike-2 (AXP6 inner header) |
| `ecc.py` | reused from spike-2 (RS(255, 223)) |
| `density.py` | NEW — sigmoid forward model |
| `solver.py` | NEW — linear LSQ in logit space |
| `germ_codec.py` | NEW — 40 bits/germ codec, no sign convention |
| `encoder.py`, `decoder.py` | NEW — composed pipeline |
| `test_roundtrip.py` | NEW — the gate |
| `tests/` | NEW |
| `results/SPIKE3_REPORT.md` | created on test run |

## How to run

```bash
cd phoxcar/spike3
python3 test_roundtrip.py --bit-depth 8     # the actual gate
python3 test_roundtrip.py --bit-depth 16    # for comparison
```

## Decision framing

If spike-3 PASSES at 8-bit, this is the **production substrate path** for Phase 1. Spike-2 (CRYPSOID-strict) becomes the reference truth-model for digital-file workflows where 16-bit is acceptable; spike-3 (sigmoid carrier) becomes the V3 (capture-mediated) production carrier.

If spike-3 FAILS at 8-bit, the substrate-display-function approach has a deeper issue and Phase 1 P3 needs further design work. Document failure mode precisely.
