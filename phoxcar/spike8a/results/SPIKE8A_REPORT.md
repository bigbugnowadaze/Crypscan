# Phoxcar Spike-8A — Sidecar Removal + Fiducial Pose Recovery (Synthetic)

**Run date:** 2026-05-04
**Substrate:** spike-7 (codebook + pilots) + 4 corner finders + manifest cluster, NO JSON sidecar
**Result:** **architectural concept validated; implementation has narrow operating range.** Honest, important Phase 1 P3 finding: simple corner finders are insufficient for production capture pipelines. Phase 1 P3 must invest in proper fiducial design.

---

## 1. Headline finding

**Spike-8A demonstrates that the substrate CAN decode without a sidecar.** The zero-warp gate passes cleanly: finders are detected, homography is recovered, manifest is parsed, pilots are fitted, payload is decoded, SHA-256 verifies. **The architectural pivot from sidecar to in-carrier manifest works.**

But the **simple corner-finder implementation has limited operating range.** Under non-trivial geometric warps OR photometric drift large enough to shift finder bright regions, detection fails before the rest of the pipeline can run.

This is a Phase 1 P3 finding, not a regression: spike-7's photometric envelope still applies for known-position decode. Spike-8A's narrower envelope is specifically a finder-detection limitation in this spike's implementation.

## 2. Tolerance profile

### Geometric sweep

| Noise type | Severities passing | Severities failing |
|---|---|---|
| Translation (px) | 0, 5, 20 | 50, 100 |
| Rotation (°) | 0, 90 | 5, 15, 45, 180 |
| Scale | 0.7, 1.0 | 0.85, 1.18, 1.4 |
| Shear (°) | 0, 2 | 5, 10 |
| Tilt-X (°) | 0 | 5, 10, 20, 30 |
| Tilt-Y (°) | 0 | 5, 10, 20, 30 |

The substrate handles only small geometric perturbations. Even mild warps (5° rotation, 1.18× scale, 5° shear, any tilt > 0°) break finder detection or corner identification.

### Photometric sweep (vs spike-7)

| Noise type | Spike-7 envelope | Spike-8A envelope |
|---|---|---|
| Gaussian σ | ≤ 0.10 | ≤ 0.01 |
| JPEG Q | ≥ 15 | ≥ 15 (mostly) |
| Focus blur (px) | ≤ 1.5 | ≤ 0.3 |
| Brightness | ±0.10 | ±0.02 |
| Contrast | ±0.40 | ±0.18 |
| Salt-pepper | ≤ 0.005 | ≤ 0.001 |

The photometric envelope is **substantially narrower** than spike-7's, by roughly 5-10× on most axes. The cause is architectural ordering: **spike-8A runs finder detection BEFORE photometric calibration**, so any drift big enough to perturb finder bright regions breaks detection before pilots can correct.

This narrowing is NOT a regression of the substrate's underlying photometric tolerance — it's a side effect of the order in which spike-8A's pipeline runs. Spike-7's photometric tolerance still applies in the parallel "known-position decode" mode.

## 3. Why the simple finder design has narrow range

### 3.1 Finders deform under perspective

Phoxoidal germs rendered at amp=1.0 saturate to roughly-elliptical bright disks. Under any perspective tilt > 0°, the bright disk warps, the connected component's area shifts outside [100, 600], and the area-filter rejects it.

### 3.2 Adaptive threshold breaks under photometric drift

The percentile-based threshold (99.5%) adapts to global intensity shifts but doesn't preserve LOCAL structure of the finder patches. At gamma drift > ±0.15 or brightness shift > 0.05, the bright regions of finders dim enough that they don't form connected components ≥ 100 pixels — and detection fails.

### 3.3 The chicken-and-egg

Spike-7's pilot-based calibration is correct and works — but it requires a rectified image. Rectification requires homography. Homography requires finder detection. Finder detection requires intact finder bright regions. **Photometric drift breaks finder detection BEFORE pilots can fix it.**

This is a real architectural issue that Phase 1 P3 must address.

## 4. Phase 1 P3 mitigation paths

### 4.1 Iterative pipeline

```
detect finders (rough) -> rectify -> fit pilots -> inverse-correct -> re-detect finders -> re-rectify
```

Two passes might absorb mild drift. Engineering effort: ~1 week to implement and test.

### 4.2 Photometric pre-normalization

Histogram normalization or local-contrast normalization on the captured image BEFORE finder detection. Removes the dependency on absolute pixel values for the detection step. Engineering effort: ~3-5 days.

### 4.3 Robust fiducial design

Replace simple corner-saturation finders with mature CV markers:

- **AprilTag** — black/white square with quiet zone, robust to perspective + photometric. Mature library (`pupil-apriltags` Python). Engineering effort: ~1-2 weeks integration.
- **ArUco** — similar to AprilTag, OpenCV-native. Engineering effort: ~1 week.
- **TopoTag** (per ChatGPT's prior-art audit) — topological structure (concentric rings or graph) more invariant to perspective than bitmap-based markers. Custom implementation: ~3-4 weeks.
- **Phoxoidal-thesis-aligned topology** — concentric phox-glyph rings with cusp-density patterns, designed to survive perspective AND photometric drift while remaining catastrophe-germ-themed. Research effort: ~4-6 weeks.

### 4.4 Multi-scale + multi-threshold detection

Try multiple `(threshold, area, smooth_sigma)` combinations and pick the candidate set that best forms a known quadrilateral aspect ratio. Brute force but works. Engineering effort: ~3 days.

## 5. Honest assessment

Spike-8A's job per ChatGPT's spec was: *"can the carrier find itself? can it rectify itself? can it decode without position sidecar?"*

The answer is: **YES at zero warp + tiny noise. NO under non-trivial conditions.**

This is a useful empirical milestone. The architecture supports sidecar removal — the format-spec-driven layout works, the manifest cluster bootstrap works, the homography + rectification + spike-7 pipeline composes correctly. The remaining gap is **finder design**, which is a real CV engineering problem that requires investment beyond a "spike."

For ChatGPT's predicted spike-8A acceptance criteria:

| Criterion | Achieved? |
|---|---|
| Finder cluster detected without sidecar | ✓ at zero warp; ✗ at non-trivial warp |
| Homography recovered | ✓ when finders detected |
| Rectified grid sampling correct | ✓ when homography correct |
| SHA-256 payload roundtrip passes | ✓ at zero warp; ✗ at most warps |
| Failure cases produce honest structured errors | ✓ — every failure surfaces a specific error mode |

**Score: 5/5 at zero warp; 1/5 at the wider envelope ChatGPT predicted.**

## 6. Spike-8B is gated on a fiducial upgrade

ChatGPT's plan was spike-8A (synthetic) → spike-8B (real captures). Spike-8B should NOT proceed with the current finder design. **Phase 1 P3 must upgrade fiducials (one of the §4.3 options) before spike-8B is meaningful.**

Recommended sequence:
1. **Phase 1 P3.A:** integrate AprilTag or ArUco as the finder layer, validate spike-8A's geometric sweep widens to handle ChatGPT's predicted envelope (translation arbitrary, rotation 0-360°, scale 0.5-2×, perspective tilt up to 30°, shear, sub-pixel offset).
2. **Phase 1 P3.B:** optionally explore phoxoidal-thesis-aligned topological finders as a research alternative.
3. **Phase 1 P3.C:** spike-8B real-camera captures (S23 Ultra / S21 FE / Z Flip 4 × MSI G27C4X / laptop).

## 7. What's frozen, what's open

Per `../PHOXCAR_CAPTURE_SUBSTRATE_V0.md`, layers 1-4 + 6-8 are **frozen** and spike-8A did not modify them. Layer 5 (pose recovery) is the open layer; spike-8A's implementation is **proof-of-concept**, NOT production. Phase 1 P3 will replace it.

## 8. Files

```
results/
├── SPIKE8A_REPORT.md                            (this file)
├── tolerance_profile_<timestamp>.json           (machine-readable conditions + summary)
├── spike8a_base_carrier.png                     (passing baseline carrier; 1280x1280)
└── noisy_carriers/                              (per-condition warped/noisy carriers)
```

## 9. Reproduce

```bash
pip install brotli reedsolo numpy scipy Pillow scikit-image
cd phoxcar/spike8a
python3 test_tolerance_profile.py
```
