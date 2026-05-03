# Phoxcar Spike-2 — Results Report (CRYPSOID-faithful)

**Run date:** 2026-05-03
**Spike scope:** `phoxoidal_carrier_proposal/10_RECOMMENDED_DECISION_FRAMEWORK.md` §5.3, follow-on to spike-1 per Bug's correction that CRYPSOID's thesis is anti-Gaussian-as-degenerate-case (and uses catastrophe-germ classification via the H² action term)
**Status:** **GATE PASS at 16-bit pixel depth.** **GATE FAIL at 8-bit.**
**Decision implication:** the production substrate has a clear pixel-depth choice: 16-bit + this exact pipeline, OR 8-bit + further engineering on the inverse fit / codec / ECC.

---

## 1. Headline numbers

| Metric | 16-bit run | 8-bit run |
|---|---:|---:|
| Payload size (varied text) | 25,923 bytes | 25,923 bytes |
| Brotli q=11 compressed | 4,177 bytes | 4,177 bytes |
| AXP6-framed | 4,236 bytes | 4,236 bytes |
| RS(255, 223) encoded | 4,849 bytes (14.5% overhead) | 4,849 bytes |
| Germs in carrier | 995 (39 bits/germ) | 995 |
| PNG dimensions | 944 × 944 | 944 × 944 |
| PNG bytes on disk | 975,274 | 280,968 |
| Sign flips applied | 430 / 995 (43.2%) | n/a |
| Extract residual (max / mean) | 1.21 / 0.008 | n/a |
| RS frames | 19 total | 19 total |
| RS frames corrected | 10 | n/a (Brotli decode failed) |
| RS bytes corrected | 54 | n/a |
| RS frames failed | 0 | n/a |
| Encode wall time | 0.28 s | 0.23 s |
| Decode wall time | 5.85 s | 6.04 s |
| Total wall time | 6.18 s | n/a |
| **Gate 1 — SHA-256 roundtrip** | **PASS** | **FAIL** (Brotli error after RS overflow) |
| **Gate 2 — RS frames decoded** | **PASS** (0 failed) | **FAIL** (decode aborted) |
| **Gate 3 — wall time < 60 s** | **PASS** (6.18 s) | n/a |
| **OVERALL** | **PASS** | **FAIL** |

## 2. The 16-bit gate — what passed

### Pipeline (CRYPSOID-faithful, all production-aligned components)

```
encode:
  payload bytes
    Brotli q=11 compress
    AXP6 inner header (verbatim from aurexis_decode.py 535-548)
    Reed-Solomon RS(255, 223) byte-stream ECC                    [+14.5% size]
    bit-pack 39 bits/germ into 5 bytes/germ
       (1 bit/germ reserved for c_ortho[0]>=0 sign convention)
    dequantize each germ to c_ortho in orthonormal basis
    convert c_ortho -> theta_raw via M_to_raw
    render carrier via CRYPSOID's strict density:
       intensity = exp(-0.5 * (mahal_sq + H(s,t)^2))
    save 16-bit grayscale PNG (lossless)

decode:
  PNG carrier
    read 16-bit grayscale
    nonlinear LM trust-region fit at each known position:
       residual = sqrt(w * I) * (-2*log(I) - mahal_sq - H(theta)^2)
       saturation mask (skip pixels at quantization floor)
       intensity-weighted (variance-optimal in log-space)
       multi-restart (+/-warm_start from spike-1 linear model)
       bounded to theta_raw in [-1, +1]^5 (codebook box)
    canonicalize sign (negate theta if c_ortho[0] < 0)
    quantize c_ortho back to 5 bytes/germ
    bit-unpack to RS-encoded byte stream
    RS decode (recovered 54 byte errors across 10 frames)
    parse AXP6 header
    Brotli decompress
    SHA-256 verify
```

### What this proves

1. The **CRYPSOID-strict H² density evaluator** (`tools/crypsorender/math/germ.py` lines 194-232) supports a working symbol-decode pathway. The catastrophe-germ classification (κ₁/κ₂ + Pearcey χ/ω + swallowtail ζ from `germ.py` lines 23-30) carries data; the inverse fit recovers the coefficients to within Reed-Solomon tolerance.
2. The **Cholesky-orthonormalized 5-coefficient basis** decouples per-coefficient noise and gives well-conditioned inverse fits.
3. **Reed-Solomon RS(255, 223)** as the byte-level ECC layer (between Brotli and AXP6 header) absorbs the residual byte-flip noise from quantization. 10 of 19 frames (52%) needed correction; total 54 bytes corrected (~3 per corrected frame, well under the 16-byte-per-frame limit).
4. **Sign convention** `c_ortho[0] >= 0` resolves the H² ambiguity at a 1-bit-per-germ cost. 43% of germs needed sign-flips at decode time, matching the expected 50% (random sign distribution).

### Per-germ inverse-fit residuals (extract layer, before RS)

- mean residual: 0.008 (clean germs decode at machine epsilon)
- max residual: 1.21 (a small fraction of germs hit local minima but the RS layer catches them)

## 3. The 8-bit gate — what failed and why

The 8-bit run reached the `parse_header` step but Brotli decompression failed: **the RS layer could not absorb the byte-flip rate produced by 8-bit pixel quantization through CRYPSOID's strict H² inverse fit.**

### Empirical byte-error rates from the smoke test (100 random germs)

| Pixel depth | Byte-exact germs | Byte error rate |
|---|---:|---:|
| 8-bit  | 61% | **14.4%** |
| 12-bit | 97% | 3.0% |
| 16-bit | 96% | 3.8% |

RS(255, 223) corrects up to 16 byte errors per 255-byte frame (6.3% threshold). At 8-bit pixel depth and CRYPSOID's strict H² inverse-fit accuracy, the byte error rate is **~2.3× the RS threshold**, so multiple frames overflow and the decompression chain breaks.

### Why 8-bit is harder than spike-1

Spike-1 used a **linear-in-coefficients** model (`intensity = baseline + amp · envelope · H`) which:
- Has no sign ambiguity (full 40 bits/germ usable).
- Has a clean linear LSQ inverse (no local minima).
- Saturates at zero "true" rate when input theta produces in-range patches.

Spike-2 uses **CRYPSOID's strict H²** model which:
- Loses the sign of θ (1 bit per germ to convention, 39 bits/germ usable).
- Requires nonlinear LM/trust-region fit (susceptible to local minima at low SNR).
- Produces patches with extreme intensity dynamic range (at moderate θ the corners drop below 8-bit's quantization floor, destroying information).

Going from spike-1's 0.30 wall time to spike-2's 6.18 s reflects the nonlinear-fit cost; going from spike-1's 8-bit-ALSO-fails to spike-2's 8-bit-fails-harder reflects the H² model's nonlinearity penalty.

## 4. What this empirically establishes for Phase 1

These findings update `phoxoidal_carrier_proposal/06_DECODER_RESEARCH_PLAN.md` and `07_INTEGRATION_BRIDGES.md`:

### 4.1 Two viable production substrate paths

The phoxoidal carrier substrate has now been empirically shown to support byte-exact decode at zero capture noise via two distinct configurations:

| Config | Forward model | Pixel depth | Bits / germ | Decoder | Wall time (995 germs) | Status |
|---|---|---|---:|---|---:|---|
| **Spike-1** | linear-in-coefs (`baseline + amp·envelope·H`) | 16 | 40 | linear LSQ | 0.31 s | PASS |
| **Spike-2** | CRYPSOID strict H² (`exp(-0.5(mahal+H²))`) | 16 | 39 + RS overhead | LM nonlinear fit | 6.18 s | PASS |
| Spike-2 | CRYPSOID strict H² | 8 | 39 + RS overhead | LM nonlinear fit | n/a | **FAIL** |
| Spike-1 | linear-in-coefs | 8 | 40 | linear LSQ | n/a | FAIL |

### 4.2 The CRYPSOID-thesis trade-off is real

Spike-1's linear forward model is faster and uses 1 more bit per germ, BUT it is not faithful to CRYPSOID's catastrophe-germ thesis (`docs/thesis_digest.md` line 11). Production substrate should use the strict H² model to remain in the spirit of the underlying mathematics. The trade-off is:

- 1 bit per germ to sign-convention overhead (≈2.5% density loss)
- ~20× decode wall time (still well under "asynchronous workflow" budgets per `08_HONEST_TRADEOFFS.md` §12)
- 16-bit pixel depth requirement at the spike's geometry

### 4.3 Open avenues for 8-bit recovery (Phase 1 research)

The 8-bit FAIL is a real datapoint, not a verdict. Several approaches could close the gap:

| Approach | Mechanism | Phase 1 effort estimate |
|---|---|---|
| **Stronger ECC** (e.g., RS(255, 175) with 32-byte correction) | Absorb 12.5% byte error rate at 36% overhead | ~1 day |
| **Iterative encoder pre-compensation** | Encoder predicts decoder's per-byte error and pre-distorts inputs to fixed-point under the encode-decode-quantize map | ~2-3 weeks |
| **Reduce bits per coefficient** (e.g., 6 or 7 bits/coef → 30-35 bits/germ) | Larger quantization step → bigger noise margin | 1-2 days; impacts density per `05_INFORMATION_DENSITY_ANALYSIS.md` |
| **Larger patches with smaller sigma** | More pixels per germ at finer detail; higher SNR for fit | 1 week of tuning |
| **Better LM initialization** | Multi-grid global search before local LM; reduces catastrophic local minima | 1-2 weeks |
| **Different forward model that's still CRYPSOID-aligned** | E.g., `intensity = exp(-0.5 mahal) · exp(amp · H)` (sign-preserving, log-linear in θ) — same catastrophe-germ basis, different action structure | 1-2 weeks; needs CRYPSOID alignment review |

### 4.4 Capture-mediated implication (V3 frontier, per Bug's framing)

For capture-mediated workflows (the V3 lane purpose), the carrier is displayed on an 8-bit panel and re-photographed by an 8-bit camera. **The 16-bit headroom does not survive the display step.** So spike-2's 16-bit success is good news for digital-file-to-digital-file workflows (where AXP6 already wins on density anyway) but does not directly address V3.

For V3, Phase 1 P3 must succeed at 8-bit OR adopt a different forward model robust to 8-bit. The 8-bit FAIL here is the leading indicator that strict H² + LM fit may not be the production decoder path for capture-mediated workflows. One of:

1. Stronger ECC (RS(255, 175) or BCH or Turbo) absorbing 8-bit's higher byte-flip rate.
2. Iterative encoder pre-compensation guaranteeing fixed-point bytes under encode-decode-quantize.
3. A different CRYPSOID-thesis-aligned forward model (sign-preserving log-linear, see §4.3).
4. Per-germ redundancy (R≥3, encoded in the proposal but the spike used R=1).

These are real Phase 1 P3 design choices the spike now makes visible.

## 5. What this still does NOT validate

Same as spike-1 (per `../spike/results/SPIKE_REPORT.md` §6):

- ❌ Noise tolerance (no synthetic noise injected beyond pixel quantization)
- ❌ Captured-image robustness (no V2/V3 protocol capture)
- ❌ Manifest cluster bootstrap (positions on JSON sidecar)
- ❌ Tier C aesthetic field interference
- ❌ Density at production scale (995 germs vs ~6M for full AXP6 sample carrier)

## 6. Files

```
results/
├── SPIKE2_REPORT.md                              (this file)
├── roundtrip_20260503T231148Z_16bit.json         (16-bit gate metrics, PASS)
├── roundtrip_20260503T231233Z_8bit.json          (8-bit gate metrics, FAIL)
├── spike2_carrier_16bit.png                      (passing 16-bit carrier; 975 KB)
├── spike2_carrier_16bit.png.manifest.json
├── spike2_carrier_8bit.png                       (failing 8-bit carrier; 281 KB)
└── spike2_carrier_8bit.png.manifest.json
```

To reproduce:

```bash
pip install brotli reedsolo numpy scipy Pillow
cd phoxcar/spike2
python3 test_roundtrip.py --bit-depth 16     # PASS
python3 test_roundtrip.py --bit-depth 8      # FAIL (Brotli decoder error)
```

## 7. Recommendation to Bug

Spike-2 confirms that **CRYPSOID's strict H² catastrophe-germ density evaluator works as a substrate for the proposed phoxoidal carrier at zero capture noise**, with 16-bit pixel depth and the standard ECC stack.

For Phase 1:

1. **Authorize the strict H² model as the production forward model.** It's CRYPSOID-thesis-aligned and empirically tractable. The linear model from spike-1 should be retained as a development sanity-check baseline, not as the production substrate.
2. **Pixel depth is a load-bearing Phase 1 design decision.** For digital-file workflows: 16-bit. For capture-mediated workflows (V3 frontier): the 8-bit problem must be solved first via one of the §4.3 options. Phase 1 P3 should explicitly fork into "16-bit digital-file" and "8-bit capture-mediated" tracks.
3. **The catastrophe-germ thesis is empirically substrate-supportable.** Bug's instinct to keep the H² (rather than spike-1's linear shortcut) is correct — at the 16-bit operating point. The finding "CRYPSOID-faithful + 16-bit = SHA-256 roundtrip works" is the right architectural-level result for this scoping spike.

Spike-1's linear simplification was a useful sanity-check; spike-2's CRYPSOID-faithful build is the empirical answer for the actual proposal. Both are kept in tree.
