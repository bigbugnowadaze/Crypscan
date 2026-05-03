# 08 — Honest Tradeoffs

> Single document collecting every "this is harder than the simple version of the proposal makes it sound" point. If a reader comes away thinking the proposal is risk-free, the writing has failed. The proposal swings big; this document swings equally big in the opposite direction.

The handoff is explicit on this point: "If the honest-tradeoffs doc is honest. If a reader comes away thinking the proposal is risk-free, the writing has failed." (`cowork_handoff_v4_phoxoidal_carrier_redesign.md` §"Success criteria for Phase 0".) The discipline of this document is to enumerate the costs, name them precisely, and not to soften them with "but here is how we mitigate" framings — mitigations live in the architecture, decoder, and bridges docs; this one names the costs.

---

## 1. The architectural commitment is irreversible-ish

Once a `.3dphox` carrier is in deployment, the inverse pipeline (germ extraction + symbol decode) must keep working. Deprecating the carrier means stranding files. AXP6 has the same property at smaller scale (an `.axp6.png` requires an AXP6-aware decoder), but AXP6's decoder is a 737-line pure-stdlib script that one engineer can re-implement in a long afternoon if the code is ever lost. The phoxoidal decoder is a multi-thousand-line composition of scale-space + persistent-homology + Mumford-Shah + germ-fit + sheaf-composition, with several library dependencies. Long-term maintainability is meaningfully harder.

The cost is **substrate inertia**. If the substrate change is wrong (`02_FAILURE_MODEL_ANALYSIS.md` §4 enumerates the ways), reverting it is more expensive than reverting AXP6 ever would be.

## 2. The encoder is real engineering, not a transcription

`03_PHOXOIDAL_CARRIER_ARCHITECTURE.md` §10 lists encoder steps 4 (germ placement in scene space, optimized for detectability, non-overlap, preservation of Tier C aesthetics, redundancy) and 5 (output `.3dphox` scene). These are not "straightforward arithmetic." They are constrained-placement-optimization problems with multiple competing objectives:

- **Detectability under expected noise** depends on choosing germ positions and scales that survive the renderer + display + capture chain.
- **Non-overlap with other germs** requires global geometric reasoning across all germs in the scene; the natural greedy algorithm produces sub-optimal packings.
- **Preservation of Tier C aesthetic field** means the placement must not create germs in regions where Tier C's natural structure dominates, and must not visually contaminate the Tier C content with discernible "data noise."
- **Redundancy** requires the R copies of each payload symbol to land at *distinct* scene positions whose joint failure probability is low — i.e., not all in one corner where a single occlusion event could take them out.

CRYPSOID has working code for *fitting* germs to existing point clouds (`fit_synthetic_germs_5()`). It does not have code for *placing* germs to encode arbitrary payload bits with the constraints above. That code is new and probably the second-largest engineering chunk after the decoder.

Expected effort: **~6-10 weeks** for a first working version of a constrained germ-placement encoder, including the optimization heuristic and verification harness. Not visible in the v4 handoff's framing.

## 3. The decoder is the largest research risk

This is enumerated in `06_DECODER_RESEARCH_PLAN.md` §4 and §6 in detail. Summary:

- **Persistent-homology runtime** on real-scale carriers (144 megapixels) may be prohibitive without aggressive tiling; if tiling breaks confidence semantics, the design needs reworking.
- **Sub-pixel localization** under realistic capture noise may not achieve the accuracy the germ-fit step requires.
- **Tier C aesthetic-field interference** with payload germs is real and may force restrictive Tier C design constraints.
- **Manifest cluster detection** without prior knowledge of carrier orientation/scale is a bootstrap problem with no clean solution.
- **Numerical stability** of the inverted germ-fit at low SNR is a real risk for the higher-order coefficients (χ, ω, ζ).

`06_DECODER_RESEARCH_PLAN.md` §4.6 estimates **6-9 months of focused single-engineer work** for a captured-image roundtrip. Honest engineering posture: the proposal will live or die on the decoder. Any plan for adopting the proposal must include explicit go/no-go gates at the synthetic-roundtrip checkpoint and the synthetic-tolerance checkpoint.

## 4. The carrier is a design surface — and that's a responsibility, not just an affordance

`03_PHOXOIDAL_CARRIER_ARCHITECTURE.md` §4 frames the unconstrained carrier appearance as an upside. It is also a downside.

- **Steganographic carriers that look like benign content raise trust-and-safety questions.** A carrier that looks like a photograph of a person or a brand asset can carry payload that the viewer does not consent to. AXP6 carriers look like noise; nobody mistakes them for real images. Phoxoidal carriers can be visually indistinguishable from natural images. Whether any deployment of the technology should require disclosure is a real question (`09_OPEN_QUESTIONS.md` §10).

- **The encoder must respect Tier C content.** A carrier that visibly degrades the photographic content (visible "germ artifacts" that look like compression noise or chromatic distortion) is a worse product than one that respects the photograph's appearance. This is a quality-of-design constraint that the encoder must enforce; failing to enforce it produces visually unpleasant carriers.

- **Adversarial use cases.** A bad actor could place a phoxoidal carrier inside an otherwise legitimate image to smuggle payload past a content moderator. AXP6's noise appearance makes this trivially detectable; phoxoidal carriers are not. (See §6 below for the broader adversarial framing.)

The "design surface" framing is correct but underdetermines the design responsibilities. Phase 1 should produce explicit guidelines for Tier C use; Phase 2+ should consider whether any structural watermark (a "this is a phoxoidal carrier" signal that detectors can pick up) belongs in the format spec.

## 5. The new substrate has wider failure modes than the old one

AXP6 fails in narrow, identifiable ways: bad PNG, wrong bit depth, magic mismatch, parity fail, CRC fail, decompress fail, hash mismatch. Each is a binary signal with a specific recovery path or a specific "ask Vince to re-send" action. The decoder can produce a precise diagnosis.

The phoxoidal decoder fails in a much wider distribution of ways: low-confidence germ detection, sheaf-composition obstruction, manifest cluster not found, partial decode of payload, partial-and-noisy decode requiring tie-breaking, etc. Producing a useful diagnostic for the user under a partial failure is harder than producing a CRC-pass-or-fail.

The cost is **diagnostic precision**. When AXP6 fails, you know what failed. When the phoxoidal decoder fails, you may know only that "the decode confidence didn't cross threshold." The user-facing implications of this need their own UX work.

## 6. Adversarial robustness is not improved (and arguably weakens)

`04_DIFFEOMORPHISM_INVARIANCE_ARGUMENT.md` §4.3 names this honestly: the proposal does not solve adversarial robustness. AXP6 has the same vulnerability; an adversary with write-access to the carrier can flip module values directly. But the *attack surface* is different in a way that may matter:

- **AXP6 attack surface:** flip 2-bit module values at known coordinates. Easy to do; equally easy to detect (CRC fails).
- **Phoxoidal attack surface:** introduce catastrophe-germ-confusable noise that flips germ classifications. Harder to do, but also harder to detect (germs are statistical features; an adversary can stay just under the noise floor of the persistence-confidence threshold).

Whether this matters depends on the threat model. For workflows where the carrier is treated as a transport with no expectation of integrity (Bug emails Bug a PNG, no adversary), the question doesn't arise. For workflows where the carrier might be tampered with (e.g., a publicly-viewable carrier), additional cryptographic measures (encrypted payload + signed manifest) are required and are *equally required for AXP6*. The proposal does not introduce this requirement; it just doesn't dissolve it either.

## 7. Density penalty is real

`05_INFORMATION_DENSITY_ANALYSIS.md` §2 calculates a density penalty of **1.5-3× more carrier area for typical payloads, up to ~10× for incompressible worst-case payloads**. This is a real cost.

For typical text/code/JSON payloads with reasonable redundancy budgets, the penalty is modest (1.5-3×). For incompressible binary payloads (video, encrypted blobs, already-compressed archives), the penalty is severe (up to 10× at the conservative-but-honest operating point).

If the deployment use case is "encode 30 MB of video into the smallest possible carrier," AXP6 wins decisively. If the use case is "encode 100 KB of text into a carrier that survives capture-mediated transport," the phoxoidal carrier's density penalty is irrelevant compared to its robustness gain. The choice depends on workflow, not on architecture preference.

## 8. The "it doesn't have to be either/or" defense has its own cost

`02_FAILURE_MODEL_ANALYSIS.md` §5 argues AXP6 doesn't have to be deleted; the two substrates can coexist. This is true and correct, *and* it has costs:

- **Two carriers to maintain.** Encoder, decoder, format spec, and CI for both. Bug-fix costs double; documentation costs double; user-facing dispatch ("which carrier should I use for this workflow?") becomes a real product concern.
- **Conceptual sprawl.** "We have a steganographic carrier" becomes "we have two kinds of steganographic carrier with different deployment regimes." Consumers of the technology have to learn the distinction.
- **Provenance/IP fragmentation.** AXP6 is Vince's; the phoxoidal carrier is a CRYPSOID + Aurexis Core composition (`09_OPEN_QUESTIONS.md` §5). Two separate IP/authorship arrangements to manage.

The single-substrate alternative (deprecate AXP6 once the phoxoidal carrier ships) has its own costs (stranding existing AXP6 users, breaking workflows that work today). The dual-substrate strategy is the safer answer; it is not free.

## 9. Composition with Aurexis Core's branches inherits their limits

The proposal composes with Aurexis Core's Branch 3 (sheaf composition), Branch 4 (3D moment invariants), Branch 5 (HDC), Branch 7 (real capture). Each is COMPLETE-ENOUGH and capstone-verified — within its declared scope.

Each is also **bounded**:

- Branch 3's sheaf composition is "a bounded executable coherence proof, not a claim of full sheaf-theory generality" (`HIGHER_ORDER_COHERENCE_BRANCH_CAPSTONE_V1.md` line 14). Obstruction detection covers 4 specific types, not arbitrary composition failures.
- Branch 5's VSA is one specific HDC implementation; if the proposal's symbol-encoding layer wants a different HDC variant, it might not compose cleanly with the V1 implementation.
- Branch 7's REAL_EVIDENCE_ANCHORING is currently STUB (`README.md` line 121: "Not a real-camera-validated system (V2 research lane addresses this; `06_PROOF_SYSTEM/` REAL_EVIDENCE_ANCHORING is currently STUB)"). The composition with Branch 7 is composition with a stub.

This isn't a criticism of Aurexis Core — bounded executable proofs are *better* engineering than unbounded promises. But it does mean the phoxoidal carrier's composition with these branches inherits their bounded scopes, and any decoder requirement that exceeds the bounded scope (e.g., needs a richer obstruction detection than Branch 3's four types) requires extending the underlying branch first. The cost shows up as **upstream Aurexis Core work that must happen before the phoxoidal lane can land**.

## 10. CRYPSOID's Tier 1 result was on geometric fit, not on rendered images

`reports/TIER_1_results.md` §"Honest reading" lines 74–82 is explicit about what the 2.0× killer ratio measures: **fit RMSE on point clouds**, not visual rendering quality on trained splat scenes with full SH/opacity machinery.

The proposal cites the 2.0× result as evidence that "phoxoidal blobs do better than Gaussians on residual structure" — which is true for the geometric-fit case. The phoxoidal carrier's use case is different: it places germs in a 2D rendered image and reads them after capture. Whether the 2.0× geometric-fit advantage translates into a 2.0× *encoded-bit-density* advantage is **not yet measured**. CRYPSOID's own Tier 2 ("trained 3DGS scenes / image-quality benchmark") is itself listed as PLANNED, not DONE (`docs/ROADMAP.md` lines 96–125). The CRYPSOID-side empirical work that would validate the proposal's density and detectability claims is itself still ahead.

The honest reading: **the empirical case for phoxoid-over-Gaussian on geometric fit is solid; the empirical case for phoxoid-over-Gaussian as a steganographic carrier substrate is unproven**. The proposal asks Bug and Vince to commit to the architectural transition partly on the strength of an empirical result that does not directly test the use case.

## 11. The math claim is sharper than the engineering can deliver

`04_DIFFEOMORPHISM_INVARIANCE_ARGUMENT.md` makes a clean theorem-level claim. The engineering implementation of that theorem will *always* fall short of the theorem in measurable ways:

- The germ extractor's classification is statistical, not exact.
- The diffeomorphism approximation breaks at occlusion, hard shadows, frame edges.
- The persistence threshold is a tuned engineering choice, not derivable from the math.
- The sub-pixel localization is bounded by sensor pitch and noise.
- The 5-coefficient basis is a finite truncation of an infinite normal-form hierarchy.

Each of these is fine in isolation. In composition, they impose a real engineering ceiling on how close the deployed system gets to the math's promise. The math promises invariance under smooth diffeomorphisms; the engineering delivers invariance-up-to-noise under approximately-smooth diffeomorphisms in a measured working envelope.

The cost is **theoretical-claim vs deliverable-claim drift**. Bug and Vince need to make sure the public framing (papers, marketing, product copy) does not over-claim what the engineering delivers; the math is a guide for engineering, not a substitute for measurement.

## 12. CPU-only doctrine slows everything

CRYPSOID's "no GPU, ever" rule (`README.md` line 88) is morally and architecturally correct — the project's reason to exist is being a 1:1 alternative to GPU-dependent state-of-the-art. The proposal carries this rule forward. **It also means every operation is slower than it could be on a GPU.** Persistent homology, Mumford-Shah, scale-space — all of these have GPU implementations that are 10-100× faster than CPU. The proposal foregoes that headroom.

For asynchronous workflows (encode once, decode at leisure), the CPU constraint is fine. For interactive workflows (real-time AR-style scanning), it is a hard constraint. AXP6's pure-stdlib decoder runs in milliseconds; the phoxoidal decoder will not. Whether the workflows that need the phoxoidal carrier's robustness can tolerate its decode latency is an empirical and product question.

## 13. Provenance and IP fragmentation

CRYPSOID is Bug's. Aurexis Core is Vince's. The composition produces something neither owns alone, and the clean-room provenance audits that both projects have run are not directly portable to the composition. (Aurexis Core's `CODE_PROVENANCE_AUDIT_V1.md` certifies V1 modules; CRYPSOID has its own implicit provenance; the new code in the phoxoidal lane has its own provenance to establish.)

The cost is **legal/administrative work** of a kind neither project has had to do at the inter-project level. `09_OPEN_QUESTIONS.md` §5 names this. It is not free; whoever sets the terms will have to sort out: who owns the new code, who can ship the result commercially, whether either project's existing license terms apply, who controls future versions, what happens if the partnership changes. None of this is a technical problem; all of it is a real-world cost of the composition.

## 14. Phase 0 does not surface every cost

This document tries to enumerate every cost that is visible from the architecture-and-research-plan level. It does not cover:

- Engineering costs of integration with end-user product surfaces (mobile apps, web UIs, CLIs).
- Operational costs of running the substrate in production (hosting, version management, telemetry).
- Compliance costs in jurisdictions with steganography regulations or accessibility requirements.
- Cost of Aurexis Core's V2 capture protocol becoming a hard prerequisite (V2 isn't shipped; V2-M3 is open per `V2_MILESTONE_GATES.md` line 13).
- Cost of upstream Aurexis Core branches needing extension (per §9 above) before the phoxoidal lane can compose with them.
- Long-tail user-facing UX work to handle the wider failure mode distribution (per §5 above).

Phase 1 should produce its own honest-tradeoffs pass before each gate; this document is the architectural-level pass.

## 15. The proposal might be wrong

This is the meta-point. The partners agreed up front (handoff §"Why this proposal exists at all"): "If it's wrong, that's fine — Bug and Vince agreed up front that throwing out wrong things to find right things is the goal." The architecture is a swing at the right answer, not a guarantee of the right answer. The cost of the swing — Phase 0's documentation effort, Phase 1's eventual feasibility build — is real and should be tracked. If the swing misses, the documentation and the synthesis are still valuable for what they reveal about both projects' substrates, but the architectural transition does not happen.

`10_RECOMMENDED_DECISION_FRAMEWORK.md` is the doc that tries to make the "is it wrong?" question answerable rather than vibes-based. The honest acknowledgement here: even with the framework, the answer is not obvious, and the partners may decide to defer the decision pending more data, redirect to v3 (the additive-layer fallback), or reject the proposal outright. Any of these outcomes is *consistent with the proposal's purpose* — Phase 0 is for informing the decision, not for predetermining it.

---

**The proposal swings big. Every cost above is real. Whether the swing's potential payoff justifies these costs is the joint decision Bug and Vince have to make.**

---

**Cross-references.** The architecture being weighed is in `03_PHOXOIDAL_CARRIER_ARCHITECTURE.md`. The math whose engineering ceiling is acknowledged in §11 is in `04_DIFFEOMORPHISM_INVARIANCE_ARGUMENT.md`. The decoder research that carries §3's risk is in `06_DECODER_RESEARCH_PLAN.md`. The questions for the partners that this doc surfaces are in `09_OPEN_QUESTIONS.md`. The decision framework is in `10_RECOMMENDED_DECISION_FRAMEWORK.md`.
