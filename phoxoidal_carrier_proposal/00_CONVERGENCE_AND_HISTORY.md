# 00 — Convergence and History

> Where this proposal comes from, who brought what, and why the partners decided the architectural question was worth swinging at instead of patching at the edges.

---

## 1. Two projects, one root concept

CRYPSOID and Aurexis Core are independent projects with independent owners and independent codebases. They were not built in coordination. They share, by accident or by deeper inevitability, the same conceptual root: **a "phoxel" or "phoxoidal" field as the substrate machine vision should reason over, instead of pixels**.

### 1.1 CRYPSOID's framing

From CRYPSOID's `README.md` (cloned at `https://github.com/bigbugnowadaze/CRYPSOID`, `README.md` lines 3–11):

> CRYPSOID is two halves of one project:
> 1. **`.3dphox`** — a tiered container format for 3D Gaussian Splat scenes. Every splat carries a tier label (`A` native render phoxoid, `B` native exact phoxoid, `C` Gaussian fallback) ...
> 2. **`crypsorender`** — a pure-CPU rasterizer that respects those tiers. Tier C splats render as standard anisotropic Gaussians. Tier A/B splats render through a **phoxoidal density evaluator** that uses a 5-coefficient germ basis from catastrophe optics (curvature κ₁/κ₂ + Pearcey cusp generators χ/ω + swallowtail ζ).

The thesis is one sentence (`docs/thesis_digest.md` line 11):

> A Gaussian splat is the exponential of quadratic distance from a center. A phoxoidal blob is the exponential of a *generated action field* — the soft action of a local surface/caustic germ. Gaussians become the boring constant-metric case of phoxoids.

The "killer metric" (`docs/thesis_digest.md` lines 124–129):

> **How many Gaussian splats does one phoxoidal blob replace at equal visual/geometric error?**

PhoxBench Tier 1 has measured this on real meshes (`reports/TIER_1_results.md` lines 11–14, 30–35): **2.0× across four real meshes (Happy Buddha, Armadillo, Doom combat, Audi A5) at every budget tested (B=32, B=64).** The advantage is empirically real, not vibes-based.

### 1.2 Aurexis Core's framing

From Aurexis Core's `README.md` (cloned at `https://github.com/KungFury87/Aurexis`, lines 17–28):

> Aurexis Core is a new kind of Engine and computer interface layer with the physical world.
> > **Aurexis Core is the code that sits between a computer's optic nerve and its brain.**
> - The **world** is primary reality
> - The **camera** is the sensory intake surface
> - The **phoxel field** is the machine's immediate observed stream
> - **Core** is the law that organizes that stream into structured, bounded, machine-usable reality

The "phoxel field" and the "phoxoidal field" are not the same construction in detail — Aurexis Core's phoxel is the camera-mediated observed stream; CRYPSOID's phoxoid is a parametric blob in a scene. But both projects reach for the same word because both are pushing on the same intuition: *the substrate machine vision should reason over is not a grid of independent pixel samples; it is a structured field with local generators*. CRYPSOID instantiates the generators as catastrophe-optic germs in 3D scene space; Aurexis Core treats the generators as the law-governed organization of the captured stream. They meet in the middle.

### 1.3 The architectural split that already matches

Independently, both projects converged on the same engine/runtime split:

- **CRYPSOID:** `.3dphox` (the format) + `crypsorender` (the renderer). FORMAT.md is a 250-line spec. The renderer is ~1,600 LoC pure numpy.
- **Aurexis Core:** "Aurexis Core" (the Engine / Codec / Standard) + "Aurexis E/D" (the Client / Wrapper / Runtime). The Core repo holds the engine; E/D lives outside.

In both cases the format/engine is treated as the durable artifact and the runtime is the swappable shell. This is the right split for the proposed phoxoidal carrier too, and one of the reasons composing the two projects feels architecturally natural rather than forced.

## 2. Future-work targets that were already someone else's done work

The synthesis surfaced several places where one project's open future-work list turned out to already exist in the other:

### 2.1 Hyperdimensional computing / VSA

Aurexis Core ships **Branch 5 — VSA / Hyperdimensional Cleanup** (`README.md` line 260, listed as COMPLETE-ENOUGH with capstone verified). HDC over a primitive vocabulary is a first-class operation.

CRYPSOID's roadmap mentions this only implicitly — its "germ + closest-point Newton" code is naturally vector-valued (5-coefficient germs) and any natural symbol-encoding layer between bytes and germs would benefit from VSA-style binding/superposition. **The hypervector-over-germs construction is something CRYPSOID would have built; Aurexis Core already has the substrate.**

### 2.2 Sheaf-style composition and cohomological obstruction detection

Aurexis Core ships **Branch 3 — Higher-Order Coherence / Sheaf-Style Composition** (`00_PROJECT_CORE/HIGHER_ORDER_COHERENCE_BRANCH_CAPSTONE_V1.md` lines 17–47): four bridges (Overlap Detection, Local Section Consistency, Sheaf-Style Composition, Cohomological Obstruction Detection), 258 assertions, all passing. Honestly framed as a "bounded executable coherence proof, not a claim of full sheaf-theory generality."

CRYPSOID's `docs/ROADMAP.md` flags **Sheaf-theoretic neighbor compatibility maps** as future v0.4+ work (`README.md` line 84: "Sheaf-theoretic neighbor compatibility maps from the thesis. v0.4+ work."). The proposed phoxoidal carrier needs exactly this kind of neighbor-compatibility check to do global integrity verification of the decoded germ field. **Aurexis Core already shipped the bounded version; CRYPSOID has the use case.**

### 2.3 3D moment invariants / view-dependent markers

Aurexis Core ships **Branch 4 — View-Dependent Markers / 3D Moment Invariants** (`README.md` line 259, capstone verified). Phoxoidal germs in CRYPSOID's 5-coefficient basis (κ₁, κ₂, χ, ω, ζ from `tools/crypsorender/math/germ.py` lines 1–10) are a specific kind of 3D moment invariant — they are the local Taylor coefficients of a surface generator, taken in a canonical local frame. The relationship is direct: **Aurexis Core's view-dependent-marker abstraction generalizes CRYPSOID's specific germ choice.**

### 2.4 Real-capture calibration

Aurexis Core ships **Branch 7 — Observed Evidence Loop / Real Capture Calibration** (capstone verified) and the entire V2 research lane (`V2_CHARTER.md`, `V2_ROADMAP.md`, `V2_CAPTURE_PROTOCOL.md`) is dedicated to closing the synthetic-to-captured gap with a controlled, repeatable, solo-feasible screen-based capture loop on a Galaxy S23 Ultra and an MSI G27C4X monitor. The protocol is locked at `V2-CAP-PROTO-1.0-LOCK` (`V2_CAPTURE_PROTOCOL.md` line 4).

CRYPSOID's PhoxBench Tier 3 ("Real reconstruction datasets — Mip-NeRF360, Tanks & Temples, DTU, ScanNet, Replica" — `docs/thesis_digest.md` line 138) is the analogous frontier in CRYPSOID's lane. **Aurexis Core's V2 protocol is the natural validation harness for any real-camera test of the proposed phoxoidal carrier.**

These four overlaps are not coincidences. They are signatures of two projects that share a deep substrate.

## 3. The Thom semiophysics lineage

Both projects sit, knowingly or otherwise, inside René Thom's **semiophysics** tradition — the program of grounding meaning in the canonical singular forms of predictive failure. This isn't decorative attribution; it constrains what the proposal claims and what it doesn't.

### 3.1 What semiophysics holds

Thom's central observation: a smooth potential function on a parameterized family of inputs has only a finite number of *generic* singular forms (the "elementary catastrophes" — fold, cusp, swallowtail, butterfly, hyperbolic umbilic, elliptic umbilic, parabolic umbilic). These are the canonical local pictures of predictive breakdown. The classification is a theorem of differential topology, not a heuristic.

Petitot, Wildgen, and others extended this into a program for grounding categorical perception and meaning in the topology of discontinuity — semiophysics. The technical content for our purposes: **the catastrophe germs are the diffeomorphism-invariant classification of generic singularities of smooth maps**. (See `04_DIFFEOMORPHISM_INVARIANCE_ARGUMENT.md` §2 for the precise statement and what it does and does not give.)

### 3.2 Why this matters for a steganographic carrier

A steganographic carrier survives transport to the extent that the features the decoder reads survive whatever happens between encoder and decoder. AXP6's pixel-grid features (8×8 module blocks at known coordinates, 2-bit module values, neighborhood-linked CRCs) survive *information loss inside a known coordinate system*. That is a real survival regime — scratches, smudges, occlusion. AXP6 is well-tuned for it.

What pixel-grid features do *not* survive is *coordinate-system warp* — the perspective tilt, rolling shutter shear, focus blur, and lens warp introduced by capturing the carrier through a real camera. Warp does not lose information; it relocates it to coordinates the decoder doesn't know how to address. Parity cannot fix that, because parity protects information *within* a coordinate system; it does not tell you where to look.

Catastrophe germs are diffeomorphism-invariant classifications. By construction, what the germ extractor reads from a captured image is invariant under the smooth coordinate transformations that warp introduces. That is a mathematical fact about the carrier substrate, not a heuristic engineering response. **This is the structural reason the proposal exists at all.**

### 3.3 What semiophysics does not give

The math gives diffeomorphism invariance, not omniscience. It does not give:
- Adversarial robustness (`08_HONEST_TRADEOFFS.md` §6).
- Robustness to extreme low-light or extreme blur where no singularities are detectable at any scale.
- Bit-density parity with the absolute best pixel-grid encodings.

`04_DIFFEOMORPHISM_INVARIANCE_ARGUMENT.md` is the doc that draws these lines precisely. The semiophysics framing is load-bearing for the architectural claim *and* it is honest about its limits.

## 4. Why this proposal exists at all (the explicit framing)

Both partners had a synthesis session. Two realizations crystallized:

1. **The carrier is the architectural unit at risk.** AXP6's payload-integrity contracts (Brotli + SHA-256 + bit-exact verification) are correct and not the problem. AXP6's pixel-grid carrier substrate is a smart engineering response to one specific failure model — discrete localized corruption. The actual failure model in the V2 frontier is *smooth continuous transformation*, and pixel-grid encodings cannot defend against that regime with more redundancy. (`02_FAILURE_MODEL_ANALYSIS.md` is the full version of this argument.)

2. **The replacement substrate is already partially built, in two places.** CRYPSOID has the math (germs, Newton solver, Tier 1 empirical 2.0×). Aurexis Core has the integration substrate (sheaf-style composition, HDC, view-dependent markers, V2 capture protocol). Composing them produces a carrier that is structurally suited to the V2 frontier in a way that incremental AXP6 patches are not.

The partners then made an explicit agreement: **the right answer is more important than preserving any specific existing engineering**. If the proposal is wrong, throwing it out clarifies what is right. If the proposal is right, the V2 frontier dissolves rather than getting incrementally chipped at. Either outcome advances the project.

This proposal is the formal authoring of the redesign for joint review under that agreement. It is not a fait accompli and it is not a sales pitch. The writing tries to make the case clearly enough that the *real* question — adopt, redirect, reject, or counter-propose — can be answered on the merits rather than on framing.

## 5. What changed from v3 to v4

The v3 cowork handoff proposed a phoxoidal layer *underneath* AXP6 — additive, low-risk, smaller architectural commitment. The v4 handoff (which this Phase 0 package executes) reframes the work as a from-foundations rebuild of the carrier substrate while preserving AXP6's payload-integrity contracts as outer wrappers.

The reason for the reframing: the additive approach buys back robustness *up to a ceiling* set by the underlying pixel-grid assumption. The diffeomorphism-invariance argument suggests that ceiling is below the V2 frontier. If that is right, v3 spends substantial engineering effort to produce something that still fails on the regime the partners actually care about. v4 swings at the architectural level instead.

v4 may be wrong. v3 is the leading "if v4 is rejected" fallback. `10_RECOMMENDED_DECISION_FRAMEWORK.md` §3 names the conditions under which v3 is the right call. Both options stay on the table until the joint review.

## 6. What this document is not

- Not a defense of either project's prior engineering choices. Both projects are well-built; the proposal is about composition under a shifted failure model, not about correcting past mistakes.
- Not an attempt to settle authorship or IP. Both partners agreed those are TBD between them and not for this Phase 0 package to predetermine. (See `09_OPEN_QUESTIONS.md` §5.)
- Not a complete history of either project. CRYPSOID's `reports/PROJECT_STATE.md` (716 lines) and Aurexis Core's `00_PROJECT_CORE/` audit set are the canonical histories; this document only excerpts what is load-bearing for the proposal.

---

**Cross-references.** The architectural detail this document gestures at is in `03_PHOXOIDAL_CARRIER_ARCHITECTURE.md`. The math claim is in `04_DIFFEOMORPHISM_INVARIANCE_ARGUMENT.md`. The engineering tradeoffs are in `08_HONEST_TRADEOFFS.md`. The open questions for the partners are in `09_OPEN_QUESTIONS.md`.
