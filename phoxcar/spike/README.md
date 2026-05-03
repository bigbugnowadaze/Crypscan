# phoxcar/spike — Phase 0.5 scoping spike

**Status:** in-progress
**Authorized:** 2026-05-03 (Bug)
**Goal:** prove or disprove that the proposed phoxoidal-carrier symbol-decode pathway works end-to-end at zero capture noise, before committing to full Phase 1.
**Acceptance gate:** SHA-256 roundtrip pass on a synthetic ~1000-germ carrier with no Tier C field, no manifest cluster, no persistent homology, no Mumford-Shah, no captured-image work, no V2-protocol noise.

This is the spike defined in `phoxoidal_carrier_proposal/10_RECOMMENDED_DECISION_FRAMEWORK.md` §5.3 and re-confirmed in `phoxoidal_carrier_proposal/ADDENDUM_01_img2phox_integration.md`. **It is deliberately the smallest test that can falsify the architecture.** If the spike's gate passes, Phase 1's main bridges (`07_INTEGRATION_BRIDGES.md` Branch P3) are justified. If it fails, the v4-vs-v3 decision is re-opened in light of empirical evidence.

## Scope (locked, no creep)

- Encoder: payload bytes → Brotli → AXP6-equivalent inner header → 8-bit-per-coefficient symbol pack into 5-coef germs → place ~1000 germs at known scene positions → emit a 2D carrier image.
- Decoder: image → at known positions → fit 5-coefficient germ → recover symbols → strip header → Brotli decompress → SHA-256 verify against the original payload's hash.
- The known scene positions are shared between encoder and decoder (no manifest cluster bootstrap; that's Phase 1).
- All germs are at fixed scale (no scale-space search).
- Render is synthetic 2D, not via CRYPSOID's full 3DGS pipeline. Each germ becomes a local intensity profile of the form `exp(-0.5 * (mahal_sq + H(s,t)²))`, matching CRYPSOID's `phoxoidal_density_germ_full()` math (`tools/crypsorender/math/germ.py` lines 194–232) at the limit of isotropic Mahalanobis.
- No Tier C aesthetic field (background is uniform 0.5).
- No noise injection (the captured-image regime is Phase 1).
- No JPEG re-encoding (carrier is saved as a lossless PNG).

## Out of scope (deliberately)

Everything in `06_DECODER_RESEARCH_PLAN.md` §3.1–3.3 except the inverse germ-fit:

- Scale-space detection (positions are known).
- Persistent homology (no confidence weighting needed at zero noise).
- Mumford-Shah localization (sub-pixel positioning is also given).
- Manifest cluster detection (manifest is implicit — the encoder/decoder share the position list).
- Sheaf-style consistency check (no obstructions to detect at zero noise).
- Redundancy vote (R=1; redundancy comes in Phase 1 when noise is added).
- Tier C aesthetic field (no contamination to filter).
- Density / placement optimization (positions are on a fixed grid).

## Pass criteria

1. Encoder writes a `.png` carrier from a payload of ≥ 1 KB.
2. Decoder reads the carrier and recovers byte-exact original payload.
3. SHA-256 of decoded matches SHA-256 of input. **This is the gate.**
4. Per-coefficient RMSE between encoded and decoded coefficients is reported.
5. Total wall time under 30 seconds on a single CPU.

## Files

| File | Purpose |
|---|---|
| `header.py` | AXP6-equivalent fixed 48-byte inner header (`aurexis_decode.py` lines 535–548) |
| `germ_codec.py` | 5-coefficient quantization + symbol packing/unpacking |
| `render.py` | Synthetic 2D renderer for germs (Gaussian × catastrophe shape) |
| `extract.py` | Inverse 5-coefficient germ fit by least-squares at known positions |
| `encoder.py` | End-to-end encode driver |
| `decoder.py` | End-to-end decode driver |
| `test_roundtrip.py` | The acceptance gate — runs encode + decode and asserts SHA-256 |
| `tests/` | Unit tests for each module |
| `results/` | Output measurements (created on test run) |

## Quantization ranges (matches CRYPSOID's coefficient bounds)

From `tools/crypsorender/math/germ.py` lines 162–166:

| Coefficient | Physical range | Quantization (8-bit) |
|---|---:|---:|
| κ₁, κ₂ | [-25, +25] | 256 levels over span 50 |
| χ, ω | [-50, +50] | 256 levels over span 100 |
| ζ | [-100, +100] | 256 levels over span 200 |

Step size: 50/256 = 0.195 for κ; 100/256 = 0.391 for χ/ω; 200/256 = 0.781 for ζ.

## How to run

```bash
cd phoxcar/spike
python3 test_roundtrip.py
```

Output is written to `results/roundtrip_<timestamp>.txt`.

## Decision rule for the spike

| Outcome | Decision |
|---|---|
| SHA-256 pass + per-coef RMSE ≤ quantization step | **Phase 1 P3 branch (decoder) is justified at the architectural level. Authorize.** |
| SHA-256 pass + per-coef RMSE > quantization step | Architectural pathway works in principle but inverse fit needs more care; tighten extract.py, re-run before Phase 1 commitment. |
| SHA-256 fail | **Architecture has a problem at the synthetic level**. Re-open v4-vs-v3 decision; do not commit to Phase 1 until problem is identified and fixable. |
| Extraction takes > 30s for ~1000 germs | Performance concern surfaced; flag for Phase 1 P3 budget but does not fail the gate. |

## Honest limits of what this spike validates

- Validates: that the encode → render → extract → decode pathway is mathematically tractable.
- **Does not validate:** any noise tolerance, any captured-image robustness, any density at scale, any manifest-cluster bootstrap, any Tier C interference resistance, any adversarial robustness, any decode latency at production scale.

The spike is a *precondition* for Phase 1, not a substitute for it.
