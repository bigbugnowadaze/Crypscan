# Phoxcar Spike-4 — Photometric Noise Tolerance Profile

**Run date:** 2026-05-04
**Spike scope:** Bug authorized as the leading indicator of V3 viability (decode success rate vs simulated camera-pipeline photometric noise)
**Status:** **PROFILE COMPLETE.** Result is honest and important: spike-3 substrate has very narrow noise margin.
**Decision implication:** Phase 1 P3 must invest in noise-tolerance engineering (per-germ redundancy R≥3 and/or stronger ECC) before captured-image work can hope to succeed.

---

## 1. Headline finding

**Spike-3's substrate at 8-bit pixel depth is essentially zero-margin under photometric noise.** Decode succeeds at exactly zero noise. Even Gaussian intensity noise σ = 0.005 (≈1.3 quant steps at 8-bit, well below typical sensor read noise) breaks the SHA-256 gate. JPEG quality 95 (visually lossless) breaks it. Brightness shift ±0.02 breaks it.

The substrate is a working *digital-file* carrier (per spikes 1-3 gate results), but **as currently configured it is not capture-ready**. The V3 frontier requires substantive Phase 1 P3 engineering on noise tolerance before captured-image experiments make sense.

This is exactly the kind of finding the spike was authorized to surface. It does not invalidate the architectural transition; it scopes the engineering work that remains.

## 2. Tolerance profile (sweep results)

Substrate: spike-3 sigmoid carrier, 8-bit grayscale PNG, 511 germs, 692 × 692 pixels, RS(255, 223). Each row applies one noise type at one severity to the rendered carrier between encode and decode; the gate is SHA-256 byte-exact recovery of the original payload.

### Gaussian intensity noise (additive, zero-mean)

| Severity (σ) | SHA-256 | Decode error mode |
|---:|---|---|
| 0.001 | **PASS** | — |
| 0.005 | FAIL | "AXP6 inner header magic" mismatch (1 byte off in first germ) |
| 0.010 | FAIL | Same |
| 0.020 | FAIL | Same |
| 0.050 | FAIL | Same |
| 0.100 | FAIL | "too short for AXP6 header" (Brotli decompressed to 0 bytes) |

**Bound: σ ≤ 0.001 passes; σ ≥ 0.005 fails.** Transitional region not characterized in this sweep.

### JPEG round-trip (encode + decode at given quality)

| Quality | SHA-256 | Decode error mode |
|---:|---|---|
| 95 | FAIL | "Brotli decoder failed" (RS recovered some bytes, not enough) |
| 90 | FAIL | AXP6 magic mismatch |
| 75 | FAIL | Same |
| 50 | FAIL | Same |
| 30 | FAIL | Same |
| 15 | FAIL | Same |

**No JPEG quality passes.** Even Q=95 (effectively visually lossless for typical content) fails because JPEG's 8×8 DCT block quantization adds correlated noise that exceeds the substrate's per-germ tolerance.

### Gaussian focus blur

| Kernel σ (px) | SHA-256 | Decode error mode |
|---:|---|---|
| 0.3 | **PASS** | — |
| 0.6 | FAIL | AXP6 magic mismatch |
| 1.0 | FAIL | Same |
| 1.5 | FAIL | Same |
| 2.0 | FAIL | Same |

**Bound: kernel σ ≤ 0.3 px passes; ≥ 0.6 px fails.** Realistic phone capture has ~0.5-1.0 px blur even at perfect focus due to optical PSF + sensor sampling.

### Gamma correction (γ)

| γ | SHA-256 |
|---:|---|
| 0.70 | FAIL |
| 0.85 | FAIL |
| **1.00** | **PASS** (no transformation) |
| 1.18 | FAIL |
| 1.40 | FAIL |

**Only γ = 1.0 (identity) passes.** The substrate has zero tolerance for gamma drift — meaning monitor-vs-camera gamma mismatch (typical in real captures) immediately breaks the decode.

### Brightness shift (additive constant)

| Δ | SHA-256 |
|---:|---|
| −0.10, −0.05, −0.02 | FAIL |
| 0 (no shift) | PASS implicitly (baseline) |
| +0.02, +0.05, +0.10 | FAIL |

**Even ±0.02 shift fails.** Equivalent to ~5 quant-step DC offset in 8-bit terms.

### Contrast scaling (k)

| k | SHA-256 |
|---:|---|
| 0.70 | FAIL |
| 0.85 | FAIL |
| **1.00** | **PASS** (no transformation) |
| 1.18 | FAIL |
| 1.40 | FAIL |

Same pattern as gamma — only the identity transform passes.

### Salt-and-pepper noise

| Rate | SHA-256 |
|---:|---|
| 0.001 | FAIL |
| 0.005, 0.010, 0.020, 0.050 | FAIL |

**No rate passes.** Even 0.1% impulse-noise rate (≈480 corrupted pixels in a 692×692 carrier) overwhelms RS(255, 223).

## 3. Why the substrate is so brittle (root cause analysis)

A targeted measurement at the codec level (no RS) confirms the bottleneck:

| Gaussian σ | Byte errors per germ | Cumulative byte error rate | RS(255, 223) tolerance |
|---:|---:|---:|---:|
| 0.000 | 0/5 | **0.0%** | ≤ 6.3% |
| 0.001 | 0/5 | **0.0%** | OK |
| 0.002 | 0–1/5 | **2.3%** | OK |
| 0.005 | 0–3/5 | **20.4%** | **3× over** |
| 0.010 | 1–4/5 | **32.3%** | 5× over |
| 0.020 | 1–5/5 | **34.2%** | saturated |

**Sharp cliff between σ = 0.002 and σ = 0.005.** Below 2.3% byte error rate, RS recovers; above ~10%, RS is overwhelmed and decode cascades into AXP6 header / Brotli failure.

The cliff is structural: spike-3's per-germ inverse fit operates near the Cramér-Rao floor of the design matrix, with no headroom. Adding *any* nontrivial noise pushes a substantial fraction of germs across a quantization boundary.

This is consistent with spike-3's clean-noise gate result (1 byte error in 5,359 RS bytes — already 0.02% byte error rate before any noise). The substrate was sitting *right at* the RS threshold even at zero noise; tiny perturbation overflows it.

## 4. What this means for Phase 1 P3

The spike-4 finding is unambiguous: **Phase 1 P3 must engineer noise tolerance into the substrate before any V2/V3-protocol capture experiments are worthwhile.** Several mitigations are concrete and orthogonal:

### 4.1 Per-germ symbol redundancy (R ≥ 3) with majority vote

Encode each payload byte in R germs at distinct scene positions. At decode, vote majority per byte. Probability of vote failure at per-germ failure rate p:

| R | p = 0.10 | p = 0.20 | p = 0.30 |
|---:|---:|---:|---:|
| 1 | 10.0% | 20.0% | 30.0% |
| 3 | 2.8% | 10.4% | 21.6% |
| 5 | 0.86% | 5.8% | 16.3% |
| 7 | 0.27% | 3.3% | 12.6% |

R=3 + RS(255, 223) closes the gap at p ≈ 0.10 (corresponding to roughly σ ≈ 0.003). R=5 reaches p ≈ 0.20 (σ ≈ 0.005).

Cost: linear in R. R=3 → 3× carrier area for same payload. R=5 → 5×.

This is in the proposal already (`03_PHOXOIDAL_CARRIER_ARCHITECTURE.md` §5.1) but the spikes used R=1. Phase 1 P3 should default to R=3 or R=5 and re-run the tolerance profile.

### 4.2 Stronger ECC

| Code | Data : Total | Overhead | Byte-error tolerance |
|---|---|---:|---:|
| RS(255, 223) (current) | 223:255 | 14.3% | 6.3% |
| RS(255, 191) | 191:255 | 33.5% | 12.5% |
| RS(255, 175) | 175:255 | 45.7% | 15.7% |
| RS(255, 127) | 127:255 | 100.7% | 25.1% |

Combined with R=3 redundancy, RS(255, 191) gets the substrate to ~σ = 0.005 reliably. The overhead is nontrivial but bounded.

### 4.3 Larger germ patches (more pixels per coefficient)

Spike-3 uses 25×25 = 625 pixels per germ for 5 unknowns. Doubling the patch to 49×49 = 2,401 pixels gives 4× more samples, ~2× SNR per coefficient. Trade-off: 4× larger carrier per germ.

### 4.4 Per-germ confidence weighting + erasure decoding

Instead of binary vote, use the per-germ fit residual as a confidence signal. Low-confidence germs become "erasures" — RS handles erasures at half the cost of errors. This is the analog of AXP6's CRC-as-localizer pattern (`01_AXP6_ARCHITECTURE_DIGEST.md` §8.2) and was proposed but unused in the spikes.

## 5. What spike-4 does NOT establish

- ❌ Geometric noise tolerance (perspective tilt, sub-pixel translation, rotation, scale, rolling shutter shear). These require manifest cluster bootstrap (`spike-5` or Phase 1 P3 manifest-cluster bridge work) and were correctly excluded from this spike's scope.
- ❌ Real captured-image robustness (V2/V3 protocol). Even photometric tolerance is insufficient evidence; geometric and Tier-C-interference are independent risks.
- ❌ Whether the right Phase 1 P3 design absorbs the noise tolerance gap with R-redundancy alone, ECC alone, or both. That is the next measurement.

## 6. Honest summary in `01_RELEASES`-style format

```
TOLERANCE PROFILE V0 (spike-4 baseline; spike-3 substrate, R=1, RS(255, 223))

  Gaussian intensity (sigma)    : [0.000, 0.001]  in-bounds
                                  [0.005, 0.010, 0.020, 0.050, 0.100]  out-of-bounds
  JPEG round-trip (quality)     : [no quality passes]
  Focus blur (kernel sigma px)  : [0.0, 0.3]  in-bounds
                                  [0.6, 1.0, 1.5, 2.0]  out-of-bounds
  Gamma correction              : [identity only]
  Brightness shift              : [identity only]
  Contrast scaling              : [identity only]
  Salt-and-pepper rate          : [no rate passes]

  CONCLUSION: substrate is digital-file roundtrip ready (zero-noise PASS),
              not capture-ready. Phase 1 P3 noise-tolerance engineering
              required before V2/V3 captured-image experiments.
```

This is the honest baseline. Phase 1 P3's job is to update this profile with a substantively wider in-bounds region.

## 7. Files

```
results/
├── SPIKE4_REPORT.md                                  (this file)
├── tolerance_profile_<timestamp>.json                (machine-readable conditions + summary)
├── base_carrier_8bit.png                             (baseline carrier; SHA-256 PASS)
├── base_carrier_8bit.png.manifest.json               (encoder manifest)
└── noisy_carriers/                                   (per-condition noisy PNGs for inspection)
    ├── noisy_gaussian_intensity_0p001.png            (PASS)
    ├── noisy_gaussian_intensity_0p005.png            (FAIL — first byte off)
    ├── noisy_jpeg_roundtrip_95.png                   (FAIL)
    └── ... (etc per condition)
```

To reproduce:

```bash
pip install brotli reedsolo numpy scipy Pillow
cd phoxcar/spike4
python3 test_tolerance_profile.py
```

## 8. Recommendation to Bug

**Authorize spike-5: per-germ redundancy + stronger RS, re-run tolerance profile.**

Concrete spike-5 design:
- R = 3 (each payload byte → 3 germs at distinct positions, majority vote)
- RS(255, 191) (32-byte correction per frame, 33.5% overhead)
- Same spike-3 sigmoid forward + linear LSQ inverse (substrate unchanged)
- Re-run the spike-4 sweep at the new substrate
- Expected outcome: in-bounds region widens to ~σ = 0.005 (Gaussian), ~Q = 75 (JPEG), ~kernel σ = 1.0 (focus blur)

If spike-5 confirms the redundancy + ECC mitigations, Phase 1 P3 has a clear path to V3-frontier robustness. If spike-5 STILL fails at σ = 0.005, the substrate-level engineering needed is deeper (larger patches, different codec basis, or a different forward model entirely).

Either way, spike-5 turns "we need to figure out noise tolerance" into a concrete, measurable, Phase-1-actionable problem with known mitigation paths.

The proposal's `08_HONEST_TRADEOFFS.md` and `09_OPEN_QUESTIONS.md` were already explicit that captured-image robustness is Phase 1 P4 work and not yet validated. Spike-4 promotes the noise-tolerance question from "Phase 1 will measure" to "Phase 1 must engineer" — a sharper framing of the same fundamental risk.
