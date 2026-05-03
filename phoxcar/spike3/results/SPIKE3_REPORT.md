# Phoxcar Spike-3 — Results Report (sigmoid display function)

**Run date:** 2026-05-03
**Spike scope:** ChatGPT's Choice 3 (renderer/carrier separation), authorized by Bug 2026-05-03
**Status:** **GATE PASS at 8-bit AND 16-bit pixel depth.**
**Decision implication:** spike-3 is the production substrate path for Phase 1. CRYPSOID-thesis-aligned, 8-bit-friendly, fast.

---

## 1. Headline numbers

| Metric | 8-bit run | 16-bit run |
|---|---:|---:|
| Payload size | 25,044 bytes | 25,044 bytes |
| Brotli q=11 compressed | 4,510 bytes | 4,510 bytes |
| AXP6-framed | 4,569 bytes | 4,569 bytes |
| RS(255, 223) encoded | 5,359 bytes (+17.3% overhead) | 5,359 bytes |
| Germs in carrier | 1,072 (40 bits/germ, byte-aligned) | 1,072 |
| PNG dimensions | 972 × 972 | 972 × 972 |
| PNG bytes on disk | 353,505 | 1,215,368 |
| Extract residual (max / mean) | 0.42 / 0.16 | 0.0017 / 0.0006 |
| RS frames corrected / failed | 1 / 0 | 0 / 0 |
| RS bytes corrected | 1 | 0 |
| Encode wall time | 0.28 s | 0.26 s |
| Decode wall time | 0.07 s | 0.09 s |
| Total wall time | 0.40 s | 0.40 s |
| **Gate 1 — SHA-256 roundtrip** | **PASS** | **PASS** |
| **Gate 2 — RS frames decoded** | **PASS** (0 failed) | **PASS** (0 failed) |
| **Gate 3 — wall time < 10 s** | **PASS** (0.40 s) | **PASS** (0.40 s) |
| **OVERALL** | **PASS** | **PASS** |

## 2. The architectural shift — renderer/carrier separation

Bug + ChatGPT's framing (2026-05-03): the original proposal conflated CRYPSOID's strict density renderer with the phoxoidal carrier's display function. They are different concerns:

- **CRYPSOID's renderer** stays the truth model for 3DGS scene rendering (`tools/crypsorender/math/germ.py` `phoxoidal_density_germ_full`, lines 194-232). Used for displaying scene reconstructions.
- **Phoxoidal carrier display** is a separate, display-optimized projection of the same catastrophe-germ structure. The carrier's job is to make the 5-coefficient (κ₁, κ₂, χ, ω, ζ) basis recoverable from a captured 8-bit image, not to faithfully reproduce CRYPSOID's 3DGS density evaluator.

Spike-3's display function:

```
intensity(s, t) = sigmoid(baseline + amp · H(s, t))
H(s, t) = κ₁s² + κ₂t² + χ(s³ − 3st²) + ω(3s²t − t³) + ζ(s⁴ + t⁴)
```

The Pearcey-class basis is **byte-identical** to CRYPSOID's. Only the action functional differs.

## 3. Why this works at 8-bit when spike-2 didn't

| Property | spike-2 (CRYPSOID strict) | spike-3 (sigmoid carrier) |
|---|---|---|
| Forward function | `exp(−0.5·(mahal_sq + H²))` | `sigmoid(baseline + amp·H)` |
| Sign of H | Lost (squared) — costs 1 bit/germ | **Preserved** — full 40 bits/germ |
| Saturation behavior | Patch corners drop below 8-bit floor at moderate θ | **Bounded in (0.01, 0.99)** with tuned amp |
| Inverse | Nonlinear LM trust-region | **Linear LSQ in logit space** |
| Local minima | Yes (H² ambiguous basins) | **None** (convex objective) |
| Pre-restart strategy | ±warm_start, multi-restart | **Not needed** |
| Sign convention | `c_ortho[0] >= 0` (1 bit overhead) | **None** |
| 8-bit byte error rate | 14.4% (over RS threshold) | **~0%** (1 byte error in 5,359 RS bytes) |
| 8-bit gate | FAIL (Brotli error after RS overflow) | **PASS** |
| Decode wall time (995 germs) | 5.85 s | **0.07 s** (84× faster) |

## 4. The amp parameter

The sigmoid input range determines whether the patch saturates. Empirical sweep at sigma=4, half_size=12, unit codebook (`amp` was the only varying parameter; 50 random germs at 8-bit pixel depth):

| amp | Byte-exact germs | Byte error rate |
|---|---:|---:|
| 0.10 | 25/50 | 12.8% (signal too weak vs pixel noise) |
| **0.20** | **50/50** | **0.0%** |
| **0.30** | **50/50** | **0.0%** ← spike-3 default |
| **0.50** | **50/50** | **0.0%** |
| 1.00 | 20/50 | 46.4% (sigmoid saturates at corners; logit blows up) |

The sweet spot is `amp ∈ [0.2, 0.5]`. Spike-3 uses `amp = 0.30`. Production substrate should derive amp_safe from the codebook bounds and patch geometry; the upper bound is set by sigmoid saturation, the lower bound by SNR vs pixel quantization.

## 5. What spike-3 empirically establishes

For Phase 1 P3 (the decoder branch):

1. **The catastrophe-germ thesis is realizable at 8-bit pixel depth.** With the right display function, the 5-coefficient Pearcey-class basis recovers byte-exact through a standard 8-bit grayscale PNG round-trip.
2. **The renderer and carrier can be different functions.** CRYPSOID's strict H² renderer is the truth model for 3DGS scene rendering; the phoxoidal carrier uses a different display function suited to the steganographic / capture-mediated use case.
3. **Linear LSQ is the right inverse.** No nonlinear solver. No multi-restart. No local minima. ~10× faster than spike-2.
4. **Reed-Solomon ECC is a useful margin but not strictly required.** At 8-bit, only 1 byte error out of 5,359 RS-encoded bytes; without RS, the SHA-256 gate would likely still pass on this payload, but RS provides a safety margin for future capture noise.

## 6. The full sweep across all three spikes

| Spike | Forward model | Spec | 16-bit gate | 8-bit gate | Wall time (1000 germs) | Bits/germ |
|---|---|---|---|---|---:|---:|
| 1 | `baseline + amp · envelope · H` (linear) | spike-speed | PASS | FAIL | 0.31 s | 40 |
| 2 | `exp(−0.5·(mahal + H²))` (CRYPSOID strict) | CRYPSOID-faithful | PASS | FAIL | 6.18 s | 39 |
| **3** | **`sigmoid(baseline + amp · H)`** (display-optimized) | **CRYPSOID-aligned + 8-bit-friendly** | **PASS** | **PASS** | **0.40 s** | **40** |

Spike-3 is strictly better than spike-1 (CRYPSOID-aligned) AND strictly better than spike-2 (8-bit + faster). It is the production substrate.

## 7. What this still does NOT validate

Same as spikes 1 and 2 — these remain Phase 1 P3 / P4 deliverables:

- ❌ Synthetic noise tolerance beyond pixel quantization
- ❌ Captured-image robustness (V2/V3 protocol capture not yet exercised)
- ❌ Manifest cluster bootstrap (positions on JSON sidecar)
- ❌ Tier C aesthetic field interference
- ❌ Density at production scale (1,072 germs vs ~6M for full AXP6 sample carrier)
- ❌ CRYPSOID format compatibility (carrier saved as plain PNG, not `.3dphox`)

Phase 1 P3 lanes A through F (per the prior conversation) are the next testing surface.

## 8. Files

```
results/
├── SPIKE3_REPORT.md                              (this file)
├── roundtrip_20260503T234542Z_8bit.json          (8-bit gate metrics, PASS)
├── roundtrip_20260503T234553Z_16bit.json         (16-bit gate metrics, PASS)
├── spike3_carrier_8bit.png                       (354 KB, passing 8-bit carrier)
├── spike3_carrier_8bit.png.manifest.json
├── spike3_carrier_16bit.png                      (1.2 MB, passing 16-bit carrier)
└── spike3_carrier_16bit.png.manifest.json
```

To reproduce:

```bash
pip install brotli reedsolo numpy scipy Pillow
cd phoxcar/spike3
python3 test_roundtrip.py --bit-depth 8     # PASS
python3 test_roundtrip.py --bit-depth 16    # PASS
```

## 9. Recommendation

**Spike-3 is the production substrate. Authorize as the Phase 1 P3 baseline.**

Spike-1 and spike-2 are kept in tree as references:
- Spike-1: linear-model sanity baseline; useful for development checks.
- Spike-2: CRYPSOID-strict reference truth; documents the renderer/carrier boundary and why we crossed it.

Phase 1 P3 (decoder branch) starts from spike-3 and adds:

1. **Manifest cluster bootstrap** — encode germ positions in the carrier itself, not in a JSON sidecar.
2. **Tier C aesthetic-field design** — make the carrier look like a photograph or brand asset by composing the sigmoid germ field with a Tier C luminance background.
3. **Synthetic capture-noise tolerance profile** — measure decode success rate under simulated camera transformations (perspective tilt, focus blur, JPEG, rolling shutter, moiré).
4. **Real V2/V3 capture roundtrip** — display on MSI G27C4X, capture with S21 FE / Z Flip 4 / S23 Ultra; decode the captured image.
5. **Density at scale** — 6M germs (full AXP6 sample carrier scale).
6. **CRYPSOID format compatibility** — write `.3dphox` v40 native germ chunks; CRYPSOID's renderer reproduces the carrier; CRYPSOID's browser viewer displays it.

Each of these is a discrete bridge per `phoxoidal_carrier_proposal/07_INTEGRATION_BRIDGES.md` (revised). Spike-3 unblocks all of them.

## 10. Honest limits

The spike does not prove the substrate works in capture-mediated workflows yet. The 8-bit pass at zero capture noise is a necessary condition for V3 — not sufficient. Phase 1 P4 (capture branch) is where the V3-frontier evidence accumulates.

The sigmoid display function is one specific carrier; ChatGPT's options 2-5 (signed-Gaussian-tanh, contour level sets, phase rings, hybrid H² + sign channel) remain open as alternative carriers if Phase 1 surfaces issues with the sigmoid path under noise or Tier C contamination. Spike-3 is the leading candidate, not the only one.
