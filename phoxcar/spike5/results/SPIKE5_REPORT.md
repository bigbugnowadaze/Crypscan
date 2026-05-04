# Phoxcar Spike-5 — R=3 + RS(255, 191) Tolerance Profile

**Run date:** 2026-05-04
**Substrate:** spike-3 sigmoid carrier + R=3 byte replication + RS(255, 191), 8-bit pixel depth
**Result:** **partial improvement.** JPEG quality envelope opens (Q=90 and Q=95 now pass; spike-4 had no JPEG passing). Gaussian noise, focus blur, gamma, brightness, contrast, salt-pepper envelopes unchanged.

---

## 1. Headline finding

**R=3 + RS(255, 191) is helpful but not sufficient.** The substrate's noise tolerance widens only modestly. This is a useful empirical datapoint for Phase 1 P3:

- The mitigation **does** add real margin against highly-localized correlated errors (JPEG block artifacts).
- The mitigation **does not** add meaningful margin against broadband random noise (Gaussian intensity, salt-pepper).
- Calibration-drift transforms (gamma / brightness / contrast) are unaffected by ECC + redundancy — they need a different mitigation strategy entirely.

The substrate has a **deeper issue** than what ECC + replication alone can address. Phase 1 P3 needs to attack per-germ SNR at the substrate level, not just compensate for it at the ECC layer.

## 2. Direct comparison: spike-4 (R=1) vs spike-5 (R=3)

| Noise type | Spike-4 in-bounds (R=1, RS(255,223)) | Spike-5 in-bounds (R=3, RS(255,191)) | Δ |
|---|---|---|---|
| Gaussian intensity (σ) | ≤ 0.001 | ≤ 0.001 | **none** |
| JPEG round-trip (Q) | none passes | **Q ≥ 90** | **NEW: Q=95, 90 PASS** |
| Focus blur (kernel σ px) | ≤ 0.3 | ≤ 0.3 | **none** |
| Gamma correction | identity only | identity only | **none** |
| Brightness shift | identity only | identity only | **none** |
| Contrast scaling | identity only | identity only | **none** |
| Salt-and-pepper rate | none passes | none passes | **none** |

**One column moved.** JPEG quality opened from "nothing passes" to "Q ≥ 90 passes." Everything else unchanged.

## 3. Why R=3 + stronger RS partially helped JPEG but not Gaussian

The vote statistics from the passing conditions tell the story:

| Condition | Unanimous votes | Majority votes | Tied | RS frames corrected |
|---|---:|---:|---:|---:|
| Zero noise | 1278 | 1 | 0 | 0 |
| Gaussian σ=0.001 | 1275 | 4 | 0 | 0 |
| **JPEG Q=95** | **1120** | **158** | **1** | **2** |
| **JPEG Q=90** | **794** | **456** | **29** | **5** |
| Focus blur σ=0.3 | 1202 | 77 | 0 | 1 |

At JPEG Q=90, 35.7% of bytes (456 + 29 = 485 / 1279) needed at least one replica to "fix" via vote, and 5 RS frames needed correction. R=3 + RS handled this load successfully.

But for Gaussian σ ≥ 0.005, the per-germ failure rate is so high (~30% per byte at the codec level) that **post-vote byte error rate stays around 21%**, exceeding RS(255, 191)'s 12.5% tolerance per frame:

| Per-germ byte error rate | Post-R=3-vote rate | RS(255, 223) (6.3%) | RS(255, 191) (12.5%) |
|---:|---:|---:|---:|
| 0.05 | 0.7% | OK | OK |
| 0.10 | 2.8% | OK | OK |
| 0.20 | 10.4% | over | OK |
| **0.30** | **21.6%** | **over** | **over** |
| 0.40 | 35.2% | over | over |

The substrate's per-germ failure rate jumps from 0% at σ=0.002 to 20%+ at σ=0.005 (per spike-4 §3). R=3 vote cuts that to 10%, then RS would handle it — except the cliff is sharp: σ=0.005 produces ~30% per-germ failure, and post-R=3-vote of 30% is 21.6%, which exceeds RS's tolerance.

So the R=3 mitigation works for **moderate** noise (per-germ rate ≤ 20%), and the JPEG-Q=90 case happens to land in that band. But for the higher-noise band that Gaussian σ ≥ 0.005 produces, the per-germ failure rate is too high for R=3 alone to recover.

## 4. Why calibration-drift transforms (gamma/brightness/contrast) failed at every severity ≠ identity

Different failure category. Gamma / brightness / contrast are not "noise" — they are deterministic intensity remappings. The decoder expects intensities in a known range; if the entire image has been gamma-corrected or brightened, every pixel's logit is shifted, every recovered θ is shifted, every byte is shifted.

ECC + redundancy don't help because **the same wrong byte is encoded R times** — vote unanimously chooses the wrong byte. The errors are correlated.

Mitigation strategies for calibration drift (Phase 1 P3 P4 territory, not spike-5):

1. **Calibration markers** — encode a known reference pattern (e.g., a fully-saturated white pixel and a fully-black pixel at known positions) so the decoder can recover the gamma curve from the captured image.
2. **Differential coding** — encode contrast between neighboring germs rather than absolute intensities. Invariant to global gamma/brightness/contrast shifts.
3. **Self-calibrating manifest cluster** — the manifest cluster's known-shape germs serve as calibration references.
4. **Histogram normalization** — at decode time, normalize the captured image's histogram to match the encoder's expected distribution.

These are all real Phase 1 P3 design choices, none of which are in spike-5's scope.

## 5. The substrate has a deeper issue: per-germ SNR margin

Spike-5 confirms the spike-4 diagnosis. The per-germ inverse fit is operating right at the noise floor with no headroom. Adding more redundancy at the byte layer is a logarithmic improvement (per-byte vote drops error rate by approximately p² for R=3, p³ for R=5), but it doesn't change the substrate-level per-germ failure rate.

To push the in-bounds region significantly, **the substrate-level fix is needed**:

| Mitigation | Mechanism | Cost | Expected effect |
|---|---|---|---|
| **Larger patches** (e.g., 49×49 vs 25×25) | More pixels per coefficient; ~√(N) noise reduction | 4× area per germ | **2× SNR per coefficient** — moves σ_threshold from 0.003 to ~0.006 |
| **Smaller sigma** (e.g., 2.0 px vs 4.0 px) | Tighter Gaussian envelope; more weight on central pixels | None directly; combines with patch size | Moves SNR to where the basis is best-conditioned |
| **R=5 or R=7 redundancy** | More replicas, lower post-vote error rate | 5×-7× area | At p=0.30: R=5 → 16% post-vote (still over RS); R=7 → 13% (marginal) |
| **Different forward model** | Less-saturating action (e.g., tanh-modulated Gaussian, contour rendering) | New code | Changes the substrate fundamentally; ChatGPT's options 2-4 from earlier |

The cleanest Phase 1 P3 attack: **start with larger patches + smaller sigma**, measure the new per-germ failure rate vs noise, then add R=3 + RS on top. If the patch-level change drops per-germ failure rate at σ=0.005 from ~30% to ~10%, then R=3 + RS handles it cleanly.

## 6. Honest summary for Phase 1 P3

| Layer of mitigation | Spike status | Effect |
|---|---|---|
| RS(255, 223) (spike-3, spike-4) | tested | Marginal at any noise above zero |
| RS(255, 191) (spike-5) | tested | Modestly better than (255, 223); not a fix |
| R=3 byte replication (spike-5) | tested | Modest; widens JPEG band only |
| R=5 or R=7 replication | not tested | Predicted modest further widening |
| Larger patches + smaller sigma | **not tested** | **Predicted to be the actual fix** |
| Calibration markers / differential coding | not tested | Required for gamma/brightness/contrast |
| Different forward model (ChatGPT options 2-4) | not tested | Open architectural alternative |

**Spike-5's takeaway: ECC + redundancy alone are not enough. Phase 1 P3 must attack per-germ SNR at the substrate level.**

## 7. Files

```
results/
├── SPIKE5_REPORT.md                                  (this file)
├── tolerance_profile_<timestamp>.json                (machine-readable)
├── spike5_base_carrier.png                           (passing baseline)
├── spike5_base_carrier.png.manifest.json
└── noisy_carriers/                                   (per-condition noisy PNGs)
```

## 8. Recommendation to Bug

**Spike-6: larger patches + smaller sigma.** Concrete config: half_size=18 (37×37 pixels = 4× more samples), sigma=2.5 (tighter envelope), R=3 + RS(255, 191) (carry over from spike-5). Re-run the same sweep and look for in-bounds widening on Gaussian noise specifically.

If spike-6 confirms patch-size scaling moves σ_threshold from 0.003 → 0.01+ (≥ 3× improvement), Phase 1 P3 has a clean path. If spike-6 doesn't move it, the per-germ inverse fit is hitting some other floor that needs a different attack (different basis? different forward model?).

Spike-5's failure to fix the gaussian-noise envelope is **important Phase 1 evidence**: the proposal's `06_DECODER_RESEARCH_PLAN.md` §4.6 estimated 6-9 months for the captured-image roundtrip with explicit go/no-go gates. Spike-5 is consistent with that timeline — there's real research-engineering to do, no quick wins, and the mitigations compose multiplicatively rather than additively.
