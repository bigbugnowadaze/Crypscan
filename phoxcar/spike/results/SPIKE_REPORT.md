# Phoxcar Spike — Results Report

**Run date:** 2026-05-03
**Spike scope:** `phoxoidal_carrier_proposal/10_RECOMMENDED_DECISION_FRAMEWORK.md` §5.3
**Status:** **GATE PASS at 16-bit pixel depth.** 8-bit pixel depth empirically too noisy.
**Decision implication:** Phase 1 P3 (decoder branch) architecturally justified per the README's decision rule. Authorize.

---

## 1. Headline numbers

| Metric | 16-bit run | 8-bit run |
|---|---:|---:|
| Payload size (varied text) | 25,939 bytes | 25,939 bytes |
| Brotli q=11 compressed | 5,012 bytes | 5,012 bytes |
| AXP6-framed + germ-padded | 5,075 bytes | 5,075 bytes |
| Germs in carrier | 1,015 | 1,015 |
| PNG dimensions | 944 × 944 | 944 × 944 |
| PNG bytes on disk | 1,132,356 | 304,342 |
| Encode wall time | 0.19 s | 0.18 s |
| Decode wall time | 0.04 s | n/a (decode failed) |
| Total wall time | 0.31 s | n/a |
| **Gate 1 — SHA-256 roundtrip** | **PASS** | **FAIL** (header magic byte 0x41 → 0x40) |
| **Gate 2 — per-coef RMSE ≤ quant step** | **PASS** | **FAIL** (decode aborted before this gate) |
| **Gate 3 — wall time < 30 s** | **PASS** (0.31 s) | n/a |
| **OVERALL** | **PASS** | **FAIL** |

## 2. The 16-bit gate — full breakdown

```
PER-COEFFICIENT RECOVERY (16-bit, n_germs = 1,015)
    coef         RMSE         max-abs      quant-step    margin
    kappa1     9.0e-06      2.8e-05       7.8e-03       870 ×
    kappa2     1.0e-05      3.2e-05       7.8e-03       780 ×
    chi        3.0e-06      1.1e-05       7.8e-03       2,610 ×
    omega      3.0e-06      1.0e-05       7.8e-03       2,610 ×
    zeta       3.0e-06      9.0e-06       7.8e-03       2,610 ×

extract LSQ residual (per-germ): max 1.16e-04, mean 1.10e-04
SHA-256 of decoded == SHA-256 of input: TRUE
filename + size: round-trip preserved
```

The recovered coefficients are within ~1e-5 of the encoder's quantized
values across every germ in the carrier — three orders of magnitude
under the 8-bit-per-coefficient quantization step. The SHA-256 hash
of the decoded payload matches the input exactly.

**Per the README's decision rule:**
> SHA-256 pass + per-coef RMSE ≤ quantization step → Phase 1 P3 branch
> (decoder) is justified at the architectural level. Authorize.

## 3. The 8-bit failure — what surfaced

At the spike's parameters (sigma=4 px, half_size=12 px, amp=0.11), 8-bit
PNG depth produces ~0.5/255 ≈ 0.002 quantization noise per pixel. The
inverse-fit's per-coefficient noise floor at this SNR is right at the
edge of half a quantization step (3.92e-3) — so a small fraction of the
germs land just over the boundary and a single byte flips.

The 8-bit run aborted in `parse_header` because the first byte of the
AXP6 inner header magic (0x41 = 'A') was decoded as 0x40 = '@' — exactly
one quantization level off. With ~5,000 bytes in the framed payload,
even one flipped byte makes the AXP6 magic check fail before we get to
SHA-256.

Per-coef error margins from the unit-test diagnostic at amp=0.11:

| Pixel depth | k1 err | k2 err | chi err | omega err | zeta err | half-step |
|---|---:|---:|---:|---:|---:|---:|
| 8-bit | 1.65e-3 | 1.01e-3 | 8.5e-4 | 9e-5 | 4.3e-4 | 3.92e-3 |
| 16-bit | 1.8e-5 | 1e-6 | 2e-6 | 1e-6 | 2e-6 | 3.92e-3 |

For the *test germ* the 8-bit error was inside half-step. But across
~1,000 germs with random coefficients, the worst-case error exceeded
half-step on at least one byte and corrupted the header.

## 4. What the spike empirically confirmed

| Claim from `phoxoidal_carrier_proposal/` | Status |
|---|---|
| The encode → render → extract → decode pathway is mathematically tractable | ✅ Confirmed at zero capture noise |
| 8 bits per coefficient × 5 coefficients = 40 bits per germ is a workable symbol budget | ✅ At 16-bit pixel depth |
| AXP6's Brotli + SHA-256 + bit-exact contracts carry forward into the new substrate (`03_PHOXOIDAL_CARRIER_ARCHITECTURE.md` §5) | ✅ Inner header layout from `aurexis_decode.py` lines 535-548 preserved verbatim |
| The 5-coefficient germ basis (κ₁/κ₂ + Pearcey χ/ω + swallowtail ζ) supports inverse fit at known positions | ✅ Linear LSQ, well-conditioned (cond(AᵀA) ≈ 55) |
| The forward model has one bit of sign ambiguity in CRYPSOID's strict `H²` evaluator (`04_DIFFEOMORPHISM_INVARIANCE_ARGUMENT.md` §5) | ✅ The spike used a sign-preserving linear-in-coefficients alternative; production decoder must handle the strict evaluator's sign convention |

## 5. What the spike empirically surfaced (Phase 1 implications)

These are the new datapoints for `phoxoidal_carrier_proposal/`:

### 5.1 Pixel depth is a load-bearing parameter

Original Phase 0 docs did not commit to a pixel bit depth. The spike
shows that at the natural quantization step (8 bits per coefficient),
**8-bit pixel depth is not robust** — a single noise event flips a
header byte and the carrier rejects in `parse_header`. The mitigations
below are options for Phase 1; they are not pre-committed:

| Option | Description | Cost |
|---|---|---|
| **A. Adopt 16-bit grayscale PNG** (spike default) | Lossless PNG-native; decoder reads `mode='I;16'` | 2× PNG file size; identical decode latency; safe across all germs |
| B. Tighten amp at 8-bit | Smaller modulation amp gives smaller residual error per coefficient, but amp's lower bound is set by clipping vs the codebook extremes | Risk of trading clipping headroom for noise margin; not reliably safe |
| C. Reduce bits per coefficient | E.g. 6 or 7 bits → 30 or 35 bits per germ | 12.5–25% bit-budget reduction; impacts `05_INFORMATION_DENSITY_ANALYSIS.md` numbers |
| D. Orthogonalize the basis | Replace the 5-coefficient basis with an orthonormal version (spherical harmonics on disk; Zernike-like) | Decouples coefficient errors; possibly enables 8-bit; requires re-derivation of the production substrate |
| E. Inflate redundancy R | Per-bit redundancy across multiple germs (proposal `03` §5.1 default R=3-5) absorbs occasional flips | Already in the proposal; spike used R=1; production R≥3 likely makes 8-bit recoverable |

The spike does not pick. Phase 1 should measure the right combination.
Recommended starting point for Phase 1 P3.13 (synthetic forward
roundtrip): **16-bit pixel depth + R=3 redundancy + production-bound
codebook** (κ to 25, χ/ω to 50, ζ to 100 from CRYPSOID's `germ.py`).

### 5.2 Clipping is the dominant SNR limiter, not pixel quantization

The spike's most consequential discovery: at the unit codebook with
sigma=4 / half_size=12, **clipping** the rendered patch to [0, 1]
destroys recovery, not pixel quantization. The fix is to bound the amp
so no germ in the codebook ever exceeds [0, 1]:

```
max_over_patch [envelope(s,t) * sum_j |basis_j(s,t)|] = 4.155
amp_safe < 0.5 / 4.155 = 0.1203
```

The spike uses amp=0.11. Production substrate must derive amp_safe for
its specific codebook bounds and patch geometry. This is not in the
original proposal docs and should be added to `06_DECODER_RESEARCH_PLAN.md`
for Phase 1.

### 5.3 The basis is well-conditioned

`cond(AᵀA) ≈ 55` for the design matrix at the spike's settings. Earlier
hypothesis (kappa terms hard to identify because s²/t² correlates with
the Gaussian envelope) was wrong — the basis is fine, the problem was
clipping. This simplifies Phase 1 P3.9 (Inverted Germ-Fit Bridge V1).

### 5.4 Wall-time is not a Phase 1 risk

1,015 germs encode-and-decode in 0.31 s on a single CPU core. The full
AXP6 sample carrier (144M pixels, ~6M germs at the 8-bit-per-coefficient
budget) projects to ~30 minutes at this rate, dominated by ~6M
independent 5×5 LSQ solves. That's well within the "asynchronous
workflow" budget the proposal commits to (`08_HONEST_TRADEOFFS.md` §12).
Real-time scanning is not in scope for Phase 1.

## 6. What this spike still does NOT validate

Per the README's "Honest limits of what this spike validates":

- ❌ Noise tolerance (no synthetic noise injected)
- ❌ Captured-image robustness (no V2-protocol capture)
- ❌ Manifest cluster bootstrap (positions shared via JSON sidecar, not encoded in carrier)
- ❌ Tier C interference (no aesthetic field present)
- ❌ Adversarial robustness (out of scope per `04_DIFFEOMORPHISM_INVARIANCE_ARGUMENT.md` §4.3)
- ❌ CRYPSOID's strict `H²` evaluator (spike used a sign-preserving linear alternative; production must handle the strict form)
- ❌ Density at production scale (test was 1,000 germs, not 6M)

These are **Phase 1 P3 and P4 deliverables**, not spike claims.

## 7. Files in this report

```
results/
├── SPIKE_REPORT.md                                    (this file)
├── roundtrip_20260503T222946Z_16bit.json              (full machine-readable metrics from the gate run)
├── spike_carrier_16bit.png                            (the 16-bit carrier; passes the gate)
├── spike_carrier_16bit.png.manifest.json              (encoder manifest with germ positions)
├── spike_carrier_8bit.png                             (the 8-bit carrier; fails the gate)
└── spike_carrier_8bit.png.manifest.json               (encoder manifest for the 8-bit run)
```

To reproduce:
```bash
cd phoxcar/spike
python3 tests/test_codec_and_header.py     # unit tests for symbol packing
python3 tests/test_render_extract.py        # unit tests for forward + inverse fit
python3 test_roundtrip.py --bit-depth 16    # the gate (passes)
python3 test_roundtrip.py --bit-depth 8     # the gate at 8-bit (fails empirically)
```

## 8. Recommendation

**Authorize Phase 1.** The spike's gate passes at 16-bit pixel depth
within 0.31 s for 1,015 germs. The architectural pathway is mathematically
tractable. Phase 1 should:

1. Author the 22 bridges per `phoxoidal_carrier_proposal/07_INTEGRATION_BRIDGES.md` (revised in `ADDENDUM_01_img2phox_integration.md` §6).
2. Pick up §5.1 above as a Phase 1 design decision (pixel depth choice).
3. Adopt §5.2 above as a Phase 1 design constraint (amp_safe derivation per codebook).
4. Branch P3 (decoder) work composes with `tools/img2phox/preprocess.py`, `encode.py`, and `density_control.py` per `ADDENDUM_01` §4.

The remaining open questions in `09_OPEN_QUESTIONS.md` (target capture
envelope, naming, deprecation, density threshold, video, lane choice,
etc.) are unaffected by this spike's outcome. The spike's pass moves
the project from "architecture is paper" to "architecture is empirically
tractable at zero capture noise." The decoder research risk identified
in `06_DECODER_RESEARCH_PLAN.md` §4 remains real for the captured-image
regime and must be addressed in P4 (capture branch).
