# 06 — Decoder Research Plan

> The catastrophe-germ extraction problem. Toolbox candidates with their tradeoffs. The riskiest unknowns named. An estimated research timeline so the reviewer can size the engineering distance from architecture to working decoder. **This is the largest single research risk in the project.** Plan accordingly.

---

## 1. The problem statement

**Given a captured 2D image of a phoxoidal carrier, recover the structured germ field that the encoder placed in the underlying 3D scene.**

Concretely: produce a list of detected germs, each consisting of:
- A canonical local frame (origin and 2D rotation in the captured image plane).
- A 5-coefficient germ vector (κ₁, κ₂, χ, ω, ζ) in CRYPSOID's basis (`tools/crypsorender/math/germ.py` lines 23–30).
- A persistence-confidence score (topological stability across scales).
- An ordering — the i-th germ in canonical decode order.

The recovered list is then handed to the symbol decoder (layer 9 of `03_PHOXOIDAL_CARRIER_ARCHITECTURE.md` §10) which performs redundancy-vote, manifest cluster decoding, payload assembly, Brotli decompression, and SHA-256 verification.

CRYPSOID's existing pipeline goes **scene → render** (forward direction). The decoder needs **rendered_image → scene_germs** (reverse direction). This is a non-trivial inverse problem, not a syntactic transform. Hence the research-plan framing.

## 2. Why the problem is hard (relative to AXP6)

AXP6's decoder is pure-stdlib Python, 737 lines, no fitting, no optimization, no statistical inference (`aurexis_decode.py`). It runs in milliseconds on the 11032×13120 sample carrier. The whole pipeline is "read bits at known coordinates, XOR them, hash the result." This is *easy* because the substrate makes it easy.

The phoxoidal decoder is fundamentally not that. It is:
- Detection of a continuous structural pattern under noise.
- Classification under a known basis but with detection-noise-floored coefficients.
- Inversion of a forward generative model (the renderer).
- Statistical inference under a known prior (the encoder placed germs from a known distribution).

Each of these is a recognizable problem-class with a recognizable-quality literature. None of them is solved end-to-end for this specific use case. The Phase 1 research-engineering task is to compose existing techniques into a working pipeline, validate on synthetic ground truth, and iterate against captured ground truth.

## 3. Toolbox candidates

Four families of techniques are candidate components. Each is well-published, has open-source CPU-only implementations available (no GPU dependency, per the hard rule), and addresses a specific sub-problem of the extraction task. None is turnkey for the proposed use.

### 3.1 Scale-space methods (Lindeberg)

**What it does.** Detect features at a continuum of scales by analyzing a Gaussian-smoothed pyramid of the image. Local extrema of normalized derivatives across scale identify singularities. The scale at which an extremum occurs gives a natural size estimate for the feature.

**Reference.** T. Lindeberg, *Scale-Space Theory in Computer Vision* (Kluwer 1994); J. M. Morel & G. Yu, *ASIFT: A New Framework for Fully Affine Invariant Image Comparison* (SIAM J. Imaging Sci., 2009).

**Fit for our problem.** Excellent for the **detection** sub-step (find candidate singular points). The maxima of (normalized) Laplacian-of-Gaussian or Difference-of-Gaussian responses across scale are exactly the kind of structural feature catastrophe germs produce. Scale gives a natural germ-footprint estimate for the closest-point Newton solver in `tools/crypsorender/math/germ.py` line 54.

**CPU-only library options.** scikit-image (`skimage.feature.blob_log`, `blob_dog`), OpenCV (`cv2.SIFT_create`, `cv2.SURF_create`), pure-numpy implementations. All CPU.

**Risk.** Not directly catastrophe-aware — it finds *blob-like* features, not specific catastrophe normal forms. Useful as a *first-pass detector* whose hits are then classified by a more germ-aware step.

### 3.2 Persistent homology (gudhi, ripser)

**What it does.** Compute topological features (connected components, loops, voids) of a sublevel-set filtration of a function (e.g., image intensity). Each feature has a *persistence* — the difference between the threshold at which it appears and the threshold at which it disappears. High-persistence features are robust; low-persistence ones are noise.

**Reference.** H. Edelsbrunner & J. Harer, *Computational Topology: An Introduction* (AMS 2010); R. Ghrist, *Elementary Applied Topology* (CreateSpace 2014); P. Bubenik, *Statistical Topological Data Analysis Using Persistence Landscapes* (JMLR 2015).

**Fit for our problem.** Excellent for the **confidence weighting** sub-step. A detected germ that survives across many scales (high persistence) is reliable; one that appears only in a narrow scale band is likely noise. This is the structural equivalent of AXP6's CRC + parity in the new substrate (see `03_PHOXOIDAL_CARRIER_ARCHITECTURE.md` §5.2).

**CPU-only library options.** **gudhi** (`pip install gudhi`, INRIA project, CPU-only, Python bindings to C++ core); **ripser** (`pip install ripser`, fastest persistent-homology computation for low-dimensional cases, CPU-only). Both are mature, well-maintained, and meet the no-GPU rule.

**Risk.** Asymptotic complexity. Persistent homology over a megapixel-scale image is non-trivial; on a 144 megapixel carrier (AXP6 sample-carrier dimensions) it is potentially prohibitive without down-sampling or block-wise processing. Phase 1 must measure end-to-end runtime; if it is unworkable, fall back to scale-space + Mumford-Shah for confidence and use persistent homology only on the manifest cluster region.

### 3.3 Mumford-Shah functional (variational singularity localization)

**What it does.** Solve the variational problem of approximating an image by a piecewise-smooth function with a small singular set (the "Mumford-Shah functional"). The minimizer's discontinuity set localizes the image's singularities to sub-pixel precision.

**Reference.** D. Mumford & J. Shah, *Optimal approximations by piecewise smooth functions and associated variational problems* (Comm. Pure Appl. Math. 1989); A. Chambolle, *Image Segmentation by Variational Methods: Mumford and Shah Functional and the Discrete Approximations* (SIAM J. Appl. Math. 1995).

**Fit for our problem.** Strong fit for the **localization** sub-step. Once scale-space methods identify candidate germ centers, Mumford-Shah refinement can pin them down to sub-pixel accuracy, which the catastrophe-classification step needs.

**CPU-only library options.** scikit-image's `skimage.segmentation.chan_vese` is a related variational segmentation; pure-numpy implementations of the Ambrosio-Tortorelli relaxation of Mumford-Shah are tractable; full Mumford-Shah is harder and may require custom code.

**Risk.** No turnkey CPU library does exactly what we need. Custom implementation is required, drawing on published Ambrosio-Tortorelli or Chambolle-style discretizations. Estimated 1-2 weeks of focused work to produce a working version, plus testing.

### 3.4 Inverted CRYPSOID germ-fit

**What it does.** CRYPSOID's `tools/crypsorender/math/germ.py` ships a *forward* germ fitter (`fit_synthetic_germs_5()` lines 105–168) that takes 3D scene point neighborhoods and computes a 5-coef germ via a least-squares fit. The forward direction is solved.

The inverse direction — given a 2D image patch around a candidate singularity, fit a 5-coef germ — is the same math run differently. Locally rotate and translate the image patch into a canonical frame around the candidate center, then fit `H(s,t) = κ₁s² + κ₂t² + χ(s³ - 3st²) + ω(3s²t - t³) + ζ(s⁴ + t⁴)` to the local intensity-gradient or surface-shape.

**Reference.** The germ math is in CRYPSOID's repo. The closest-point Newton solver (`closest_point_on_germ()` lines 54–95) is the relevant template.

**Fit for our problem.** This is the **classification** sub-step. Once a candidate singularity has been detected (3.1) and localized (3.3), CRYPSOID's existing germ math, run inversely, classifies it into the 5-coefficient basis.

**CPU-only library options.** CRYPSOID's existing code, ported to operate on 2D image patches around captured-image candidates rather than on 3D scene neighborhoods. Pure numpy + scipy.

**Risk.** Lowest of the four — the math is owned by Bug, the code is in the repo, the only work is adapting input/output conventions. Estimated 1-2 weeks for a first working version.

### 3.5 Composition diagram

```
captured image
     │
     ▼  3.1 scale-space detection
candidate singular points (with scale estimates)
     │
     ▼  3.3 Mumford-Shah localization
sub-pixel singular points
     │
     ▼  3.4 inverted CRYPSOID germ-fit
5-coefficient germ vectors per candidate
     │
     ▼  3.2 persistent homology
persistence-confidence scores per detected germ
     │
     ▼  symbol decoder (out of scope for this doc)
```

The four techniques are complementary, not competitive. Each handles a sub-problem the others handle poorly.

## 4. The riskiest unknowns (named)

These are the items most likely to cause the Phase 1 build to either take longer than estimated or produce a decoder that doesn't meet success thresholds. They are listed in roughly decreasing order of risk.

### 4.1 Persistent-homology runtime on real-scale carriers

The 144-megapixel sample carrier is at the upper end of what persistent-homology libraries can chew through in reasonable time without aggressive downsampling. If end-to-end decode of one carrier takes hours instead of seconds, deployment economics collapse.

**Mitigation paths (in order of preference):**
1. Tile the carrier into ~1k×1k regions and run persistent homology per tile, then stitch. Confidence scores are local anyway.
2. Use scale-space confidence (number of scales at which a feature appears with consistent classification) as a cheaper proxy for persistence, reserving full persistent homology for the manifest cluster.
3. If neither tiling nor proxy works, accept slower decode for the V1 of the phoxoidal decoder and optimize in a v2.

### 4.2 Sub-pixel localization accuracy under realistic capture noise

Scale-space + Mumford-Shah jointly should achieve sub-pixel localization in the lab; under V2-protocol captures (handheld, JPEG-encoded, mid-range phone) the accuracy may degrade. If localization is off by more than a fraction of the germ footprint, the germ-fit step (3.4) inherits a positional error that biases the recovered coefficients.

**Mitigation paths:**
1. Measure localization error vs SNR experimentally.
2. Iterative refinement: detect → localize → fit → re-localize using fitted germ as prior → re-fit.
3. If unrecoverable, increase germ footprint at encode time (cost: density penalty per `05_INFORMATION_DENSITY_ANALYSIS.md`).

### 4.3 Tier C aesthetic-field interference with payload germs

Tier C is the "carrier looks like a photograph" layer. A photographic field has its own catastrophe singularities (object boundaries are folds; specular highlights can be cusps). Distinguishing these from payload germs is non-trivial.

**Mitigation paths:**
1. Place payload germs in scene regions where Tier C is band-limited (smooth ambient backgrounds; avoid places with strong natural singularities).
2. Use the persistent-homology score to filter — payload germs should have a known characteristic persistence range; Tier C germs may sit outside it.
3. Use the manifest cluster's known location to anchor decoder ordering, then read payload germs by structural neighborhood from the cluster outward.
4. If unrecoverable, accept that "the carrier looks like a photograph" is harder than "the carrier looks like an ambient texture" and design carriers accordingly.

### 4.4 Manifest cluster detection in the absence of any prior knowledge

The decoder's first job is to find the manifest cluster. The cluster is a known-shape germ-cluster pattern at a canonical location, but if the capture has rotated, scaled, or warped the carrier strongly enough, that "canonical location" is unknown.

**Mitigation paths:**
1. Make the manifest cluster *structurally distinctive* — a high-redundancy, high-persistence, high-symmetry germ pattern that is detectable even before the rest of the carrier is parsed.
2. Use rotational and scale invariants (moments) to recognize the cluster regardless of orientation.
3. Bootstrap from any detectable germ pattern: detect all candidate clusters, attempt manifest decode against each, succeed when the SHA-256 self-check passes.

### 4.5 Inverted CRYPSOID germ-fit numerical stability under noise

The forward germ-fit (`fit_synthetic_germs_5()`) operates on dense 3D point clouds with known geometry. The inverse fit operates on 2D image patches with detection noise. The least-squares system may be ill-conditioned at low SNR, especially for the higher-order coefficients (χ, ω, ζ — the cubic and quartic terms have smaller coefficient magnitudes in the basis fit and are most affected by noise).

**Mitigation paths:**
1. Ridge-regression in the fit (CRYPSOID already does this — `germ.py` line 154: `ridge = 1e-6 * np.eye(5)`); tune the ridge value for noisy 2D inputs.
2. Coefficient-bounded fit (CRYPSOID already does this — `germ.py` lines 162–166 clamp κ, χ/ω, ζ to physical ranges); apply the same bounds in the inverse fit.
3. Constrained quantization: the encoder uses 8-bit quantized coefficients, so the inverse fit should snap to the nearest quantized lattice point rather than fitting in the full continuous space.

### 4.6 Decoder development time

The composition of techniques (3.1 + 3.2 + 3.3 + 3.4) plus glue + manifest detection + redundancy decoding + symbol assembly is a substantial codebase. Honest estimate of effort to a first working synthetic-roundtrip decoder:

| Component | Estimated effort | Risk multiplier |
|---|---:|---:|
| 3.1 scale-space detection (off-the-shelf) | 1 week | 1.0× |
| 3.4 inverted germ-fit (port from CRYPSOID) | 1–2 weeks | 1.5× |
| 3.3 Mumford-Shah localization (custom) | 2 weeks | 2.0× |
| 3.2 persistent homology (off-the-shelf, integration work) | 1 week | 1.5× |
| Manifest cluster detection (new) | 2 weeks | 2.0× |
| Symbol decoder + redundancy vote | 1 week | 1.0× |
| Synthetic test harness (no captures) | 1 week | 1.5× |
| Integration + first synthetic roundtrip | 2 weeks | 2.0× |
| Captured-image roundtrip (V2 protocol) | 4 weeks | 3.0× |
| **Subtotal (most-likely)** | **~15 weeks** | — |
| **Subtotal (with risk multipliers)** | **~30-40 weeks** | — |

A working captured-image roundtrip on a representative payload, validated against V2 capture protocol, is on the order of **6-9 months of focused single-engineer work**, plus iteration. This is large compared to AXP6's existence (a working AXP6 encoder + decoder exists today). It is the cost of the substrate change.

## 5. Validation plan (per Aurexis Core convention)

The decoder should be validated against the same kind of bridge-and-capstone discipline Aurexis Core uses (`00_PROJECT_CORE/HIGHER_ORDER_COHERENCE_BRANCH_CAPSTONE_V1.md` template; see also `00_PROJECT_CORE/CAPTURE_TOLERANCE_BRIDGE_V1_GATE_VERIFICATION.md` for an analogous bridge that introduces a tolerance profile). Each step has its own gate:

1. **Synthetic forward-roundtrip gate.** Encoder produces a `.3dphox` carrier; renderer produces a PNG; decoder recovers the payload byte-exact under zero capture noise. Pass criterion: SHA-256 match.
2. **Synthetic noise-tolerance gate.** Same as #1 but with progressively stronger synthetic noise (additive Gaussian, JPEG compression, perspective tilt, focus blur). Pass criterion: a tolerance profile matching Aurexis Core's `V1_TOLERANCE_PROFILE` style (`CAPTURE_TOLERANCE_BRIDGE_V1_GATE_VERIFICATION.md` §"Tolerance Profile Summary" — scale 0.90–1.10, blur radius ≤ 2, noise amplitude ≤ 25, etc.) within which the decode succeeds; honest failure outside it.
3. **Captured-image roundtrip gate.** A real V2-protocol capture decodes byte-exact. Pass criterion: SHA-256 match against original payload.
4. **Working-envelope characterization gate.** A measured decode-success curve as a function of capture-protocol parameters (tilt, distance, lighting) is produced. Pass criterion: documented decode-success ≥ 95% inside the V2-protocol envelope, with honest failure-mode taxonomy outside.

Each gate produces a verification document in the format of `CAPTURE_TOLERANCE_BRIDGE_V1_GATE_VERIFICATION.md` (gate checks, status PASS/FAIL, tolerance profile summary, known limitations). This is consistent with both projects' existing engineering discipline.

## 6. What this plan does not commit to

- **A specific bit budget per coefficient.** The 8-bit-per-coefficient default is a placeholder; Phase 1 measurement determines the right allocation.
- **A specific manifest cluster shape.** The architecture says "a known-shape germ cluster at a canonical location"; Phase 1 design determines what shape works best.
- **A specific Tier C aesthetic-field-design constraint.** The risk in §4.3 may indicate that "no high-codimension natural singularities in Tier C" is needed; Phase 1 measurement tells us.
- **A specific real-time decode rate.** AXP6's decoder is fast (milliseconds); the phoxoidal decoder is realistically slower. How much slower is a Phase 1 measurement.
- **A specific success threshold under V2-protocol capture.** The proposal targets > 95% decode success in the V2 envelope but does not commit to a number; Phase 1 measurement and tuning sets the actual deployable threshold.

## 7. Honest framing for the reviewer

The decoder is the largest single research risk of this proposal. The math is clean (`04_DIFFEOMORPHISM_INVARIANCE_ARGUMENT.md`); the architecture is composable (`03_PHOXOIDAL_CARRIER_ARCHITECTURE.md`); the substrate density numbers are workable (`05_INFORMATION_DENSITY_ANALYSIS.md`). But none of those guarantees that the four techniques in §3 can be composed into a robust extractor in the time-and-effort budget of §4.6.

If Bug and Vince adopt this proposal, the decoder build is the chunk where the proposal will live or die. Phase 1 should be planned with this in mind: explicit go/no-go gates after the synthetic forward-roundtrip (gate #1 in §5) and after the synthetic noise-tolerance (gate #2). If gate #1 cannot be reached within ~3 months, that is strong signal that the architecture is harder to realize than this proposal expects, and the partners should re-open the decision (likely toward the v3 additive-layer fallback).

Honest engineering posture: build the synthetic gates first, learn fast, decide on captured-image work only after the synthetic decoder works. Do not commit to the V2-protocol roundtrip until the synthetic roundtrip is solid. This is the same discipline Aurexis Core's V2 charter applies to itself (`V2_CHARTER.md` §"Execution constraints" line 84: "Solo-feasible end to end / Honest reporting of limitations at every milestone").

---

**Cross-references.** The architecture being decoded is in `03_PHOXOIDAL_CARRIER_ARCHITECTURE.md`. The math the decoder relies on is in `04_DIFFEOMORPHISM_INVARIANCE_ARGUMENT.md`. The bridges that gate the decoder build are in `07_INTEGRATION_BRIDGES.md`. The honest tradeoffs the decoder must navigate are in `08_HONEST_TRADEOFFS.md`.
