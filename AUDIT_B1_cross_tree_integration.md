# B-1 — Cross-Tree Integration Audit

**Authored:** 2026-05-04
**Scope:** an honest map of where the dual-fiber substrate (visual × predicate) **actually exists** across CRYPSOID + Aurexis + the phoxoidal carrier work, and where it is currently claimed but not built.
**Purpose:** empirical ground for B-3 (naming) and B-2 (formal sketch). A name should not be applied to a substrate whose architectural state is unverified.
**Method:** read each tree's primary docs and source through the lens of `VISION_MANIFESTO.md` §III ("dual fiber"). Categorize each component as `BUILT`, `PARTIAL`, or `CLAIMED`.

---

## 1. The trees being audited

| Tree | Primary purpose | Native target | Status |
|---|---|---|---|
| **CRYPSOID** | 3D rendering substrate that generalizes Gaussian splatting via catastrophe-germ chart action | 3D scenes (`.3dphox`) | Tier 0/1 PhoxBench results published; Tier 2 (real Audi 3DGS) plumbing in progress; no germ-converter run on real data yet |
| **Aurexis Core / Phoxelis Vision Language** | Typed-predicate calculus over visual FieldBundles with 5-valued confidence + Independence Ratio scoring | 2D images / image stacks | V1 substrate frozen (ACOR-1.1); V2 active on `working/core-v2`; Phoxelis .phox file format demonstrates predicate-state-grid (Round 37c: 2 KB through PNG) |
| **Phoxoidal carrier proposal** | Screen-camera-survivable 2D byte carrier built on the same catastrophe-germ basis | 2D PNG carriers | Spike-9B-prime: synthetic-channel SHA-256 round-trip, σ=8 channel-matched substrate, full envelope characterized |

All three exist. None has been integrated with the others through anything stronger than citation.

---

## 2. Visual fiber — what's BUILT

| Component | Tree | Status | Evidence |
|---|---|---|---|
| 5-coefficient catastrophe-germ basis (κ₁, κ₂, χ, ω, ζ) | CRYPSOID | **BUILT** | `tools/crypsorender/math/germ.py` lines 23-30; `recovery_v2/THESIS.txt` (2,059 lines, Apr 2026) |
| Cholesky-orthonormalized basis on Gaussian-weighted patch inner product | Phoxoidal carrier | **BUILT** | `phoxcar/spike9b/basis.py`; reused across all spikes |
| .3dphox 3D file format (magic, manifest, tier-aware chunks) | CRYPSOID | **BUILT** | `docs/FORMAT.md`; `tools/crypsorender/io/phox_loader.py` (~250 LoC) |
| .phox 2D predicate-grid format (predicate states over cells) | Aurexis | **BUILT** | `07_VISION_SUBSTRATE/phoxelis_sim/phox_format.py` |
| Phoxoidal carrier 2D PNG codebook substrate | Phoxoidal carrier | **BUILT** | spike-9B (σ=8 + image-NCC + multi-pilot, channel-survival demonstrated) |
| img2phox compiler (image → 3D phoxoidal scene) | CRYPSOID | **BUILT** | `tools/img2phox/` (26 files, 5,872 lines per ADDENDUM_01) |
| Aurexis FieldBundle dtype system (image, regions, vector, label, ...) | Aurexis | **BUILT** | `07_VISION_SUBSTRATE/aurexis_workbench/vision_ops.py`; 32 vision operators registered |

**Honest read:** the visual fiber is rich and largely built. Multiple file formats, multiple working compilers/decoders, real published results. What's missing isn't visual-fiber components — it's a *unified* visual-fiber type system.

---

## 3. Visual fiber — what's PARTIAL or CLAIMED

| Component | Tree | Status | Gap |
|---|---|---|---|
| Catastrophe-germ tier-aware rasterizer | CRYPSOID | **PARTIAL** | Plumbing exists; Tier A/B paths defined but no real germ data has been converted from Audi PLY to phoxoid yet. Renders today still go through Tier C (Gaussian) fallback for all data |
| Native germ chunks in .3dphox (`germ_5coef_f16`, `germ_index_u32`) | CRYPSOID | **CLAIMED** | `docs/v40_native_germ_chunks_spec.md` defines the format; no .3dphox file in the repo currently uses these chunks |
| Phoxoidal carrier with Brotli + AXP6 + RS payload through screen-camera | Phoxoidal carrier | **PARTIAL** | Synthetic channel demonstrated (spike-9B); real-camera (spike-9C) deferred — substrate works in synthetic, real-capture validation pending |

---

## 4. Predicate fiber — what's BUILT

| Component | Tree | Status | Evidence |
|---|---|---|---|
| Typed predicate DSL (text-based, type-checked, persistable as JSON) | Aurexis | **BUILT** | `07_VISION_SUBSTRATE/VISION_LANGUAGE_v0_1.md` |
| 96+ vision predicates over color, structure, composition, depth, lighting | Aurexis | **BUILT** | `data/vision/vocab.aurex` |
| 32 vision operators (image → image, image → regions, regions → bool, etc.) | Aurexis | **BUILT** | `07_VISION_SUBSTRATE/aurexis_workbench/vision_ops.py` |
| 5-valued confidence lattice (TRUST/HOLD/DOWNGRADE/REJECT/NEED_MORE_EVIDENCE) | Aurexis | **BUILT** | `06_PROOF_SYSTEM/aurexis_research_sim/reports/PROOF_INDEX.md` |
| 8 primitive families (cardinality, repetition, role_zone, ordering, symmetry, adjacency, orientation, hierarchy) | Aurexis | **BUILT** | proof system reports per-family |
| Independence Ratio metric (per-predicate, per-corpus) | Aurexis | **BUILT** | Workbench harness, scored on every vocabulary install |
| Engine-semantics proof system v0.6 | Aurexis | **BUILT** | `06_PROOF_SYSTEM/aurexis_research_sim/` |
| Identity layer interface (external classifier hook, no built-in models) | Aurexis | **BUILT (interface only)** | `07_VISION_SUBSTRATE/IDENTITY_LAYER_DESIGN.md` — explicit architectural choice that identity recognition is outside the substrate |

**Honest read:** the predicate fiber is similarly rich. Aurexis is the most architecturally mature of the three trees — V1 frozen as ACOR-1.1, working test suites, proof-system reports, predicate vocabulary scored by Independence Ratio.

---

## 5. Predicate fiber — what's PARTIAL or CLAIMED

| Component | Tree | Status | Gap |
|---|---|---|---|
| 4 sheaf-style composition bridges (overlap, local-section, sheaf composition, cohomological obstruction) | Aurexis | **PARTIAL** | `00_PROJECT_CORE/HIGHER_ORDER_COHERENCE_BRANCH_CAPSTONE_V1.md` defines the four bridges; per-bridge gate verifications exist; full multi-image cohomological composition not yet exercised end-to-end |
| Capture-tolerance bridge (`V1_TOLERANCE_PROFILE`) | Aurexis | **BUILT (V1) / EXTENDING (V2)** | V1 profile measured; V2 extending to real-capture envelope (V2-M3 / V2-M6) |
| Cellular-sheaf diffusion on artifact grid | Aurexis | **CLAIMED (research)** | `RESEARCH_deep_cross_domain.md` #17 ranks high-impact; not in V1 substrate |

---

## 6. The dual — where the fibers ACTUALLY meet

This is where the audit is least flattering and most useful.

| Integration claim | Status | Detail |
|---|---|---|
| CRYPSOID germ basis is consumed by an Aurexis predicate | **NOT BUILT** | None of Aurexis's 96+ predicates take catastrophe-germ coefficients as input. The predicate fiber currently operates on generic image_stack / regions / scalar dtypes, not on germ-typed fields |
| Aurexis predicates verify a CRYPSOID-rendered 3D scene | **NOT BUILT** | CRYPSOID renders to PNG; Aurexis can decompose any PNG via its predicates; but there is no dedicated bridge that would let predicates reason about the *germ structure* of the rendered scene as opposed to its pixels |
| Phoxoidal carrier carries a *predicate signature*, not bytes | **NOT BUILT** | The carrier proposal's payload is opaque bytes (RS-encoded, Brotli-compressed). There is no "predicate-bundle" payload type. The catastrophe-germ basis is used as a transmission medium for bytes, not as a notation for verdicts |
| Sheaf-cohomological composition of multiple carriers | **NOT BUILT** | Aurexis's 4 sheaf bridges exist as architectural concepts; no two phoxoidal carriers have been composed via cohomological consistency to derive a joint verdict |
| Audit trail unified across trees (germ derivation × predicate composition × confidence states) | **NOT BUILT** | Each tree has its own audit format. CRYPSOID has run-reports per render. Aurexis has per-predicate evidence with confidence states. The carrier has Brotli + RS + SHA. There is no single audit format that traces a claim from raw image through germ basis through predicate composition through confidence verdict |
| Cross-modal interoperability (3D scan + 2D photograph + carrier all decompose into same primitives) | **NOT BUILT** | The thesis says they should; no artifact has been tested |

**Headline:** the dual-fiber substrate has been articulated (in VISION_MANIFESTO and ADDENDUM_07) and partially implemented in each tree separately, but **the dual itself — the place where a typed visual field has a typed predicate signature and they agree by construction — does not exist as code or as a single artifact**. The substrate as currently shipped is three parallel slices that share thematic vocabulary but no actual interface.

---

## 7. Specific gaps, with what would close each

| # | Gap | Smallest closing artifact | Effort |
|---|---|---|---|
| **G1** | No shared type system across the three trees | A single `phoxoid_field` dtype that all three trees can produce and consume — concretely, an Aurexis FieldBundle containing CRYPSOID-style germ coefficients, decodable by the carrier's pipeline | 1-2 weeks |
| **G2** | No Aurexis predicate operates on catastrophe-germ primitives | One predicate, e.g. `germ_signature_present(field, target_signature) → bool`, with a registered operator that reads a phoxoid_field and matches its structure against a catastrophe-type signature (fold, cusp, swallowtail) | 3-5 days |
| **G3** | No phoxoidal carrier carries a predicate signature | A new payload type for the carrier — instead of opaque bytes, a serialized predicate AST + expected-evaluation. Decoder rebuilds the AST and can evaluate it against fresh visual context | 1 week |
| **G4** | No multi-carrier sheaf composition | Two phoxoidal carriers, both decoded; their predicate-decompositions composed via Aurexis's existing sheaf-bridge code (already partially built per HIGHER_ORDER_COHERENCE_BRANCH_CAPSTONE_V1) | 3-5 days (uses existing sheaf machinery) |
| **G5** | No unified audit format | One JSON schema that traces: image_input → germ_decomposition → predicate_evaluation → composition_chain → final_verdict_with_confidence. Every intermediate step is timestamped, hash-anchored, and humanly readable | 1 week (mostly schema design + adapters in each tree) |
| **G6** | No cross-modal demonstration (3D / 2D / carrier all yielding same predicate signature) | One small worked example: a synthetic 3D phoxoid scene rendered to a 2D image; a phoxoidal carrier embedded in that image; predicate decomposition shows the same fold-catastrophe structure detected in all three artifacts | 1-2 weeks (depends on G1) |
| **G7** | Real-camera validation of the phoxoidal substrate | spike-9C (already scaffolded; awaiting Bug's capture session) | hours, when convenient |

**Critical-path observation:** G1 (shared type system) is the keystone. Without it, G2-G6 cannot cleanly interoperate. With it, the others compose. G1 should be the first integration target if the partnership decides to build the dual rather than continue articulating it.

---

## 8. Honest summary

**What exists today, in plain language:**

The partnership has built three *components* of a dual-fiber substrate. Each component is mature within its own tree. CRYPSOID gives the geometric vocabulary. Aurexis gives the predicate calculus. The phoxoidal carrier gives the screen-camera transport.

**What does not exist:**

The dual itself. Today, the visual and predicate fibers are connected by *citation* (the proposal cites Aurexis, Aurexis cites CRYPSOID's lineage, etc.), not by *interface*. A single typed object that lives in both fibers does not exist. A predicate that consumes catastrophe-germ structure does not exist. A carrier whose payload is a verdict does not exist.

**The substrate is therefore in this state:**

- Vocabulary: ✓ (catastrophe-germ basis, working code)
- Grammar: ✓ (predicate calculus, 96+ predicates, working DSL)
- Semantics: ✓ partial (5-valued confidence, sheaf bridges defined)
- **Their integration: ✗** (the slices haven't been wired together)

If we name this today, we'd be naming an aspiration. If we wire G1 (and ideally G2 + G5), we'd be naming a working substrate.

---

## 9. Implications for B-3 and B-2

**For B-3 (naming):** the substrate currently has three names that point at three slices. Choosing a single name is a **commitment** — to integrate the slices, to make the dual real, to stop calling the slices the system. The audit suggests the partnership is one or two weeks of focused integration work away from being able to name the whole honestly. Naming earlier is naming an intent; naming later is naming a thing.

**For B-2 (formal sketch):** the predicate calculus is the most formalizable component today, and Aurexis already has substantial formal infrastructure (DSL, type-checker, IR scoring, proof system). The catastrophe-germ basis is well-defined mathematically and is also formalizable (CRYPSOID's thesis is published). The hard formalization work is the **dual** — defining the type-theoretic structure that lets a typed visual field have a canonically-derived typed predicate signature. That formalization should wait until G1 has been attempted in code, because the right type signature will emerge from the integration attempt.

---

## 10. What I'm recommending

**Short version:** before B-3 and B-2, do at least G1 — a shared type system across the trees. Without it, naming and formalization are downstream of vapor.

**Concrete next step (proposed):** a 1-page integration spec for the `phoxoid_field` dtype that CRYPSOID, Aurexis, and the carrier can all produce and consume. Not a build. A *spec* that the three trees' maintainers (Bug + Vince + Claude) agree on, after which one of the three rewrites its boundary to honor the spec.

That spec, drafted, is itself the output of the next step. From there, the integration becomes a series of small surgical edits in each tree, not a new system to invent.

If the partnership wants to defer integration and proceed with B-3 (naming) on the current state, that's a legitimate choice — it makes the manifesto more concretely available for outside reading. But the audit says: **the name will be paying for an integration that hasn't been done yet.**

---

## 11. What this audit is not

- Not a plan. The gaps list is descriptive, not prescriptive.
- Not a critique of the work. The components are excellent. The integration is the missing piece.
- Not exhaustive. The audit was time-boxed; deeper reads of CRYPSOID's `THESIS.txt`, Aurexis's `Higher-Order Coherence Branch`, and the proof system reports could reveal more existing integration than I found.
- Not a replacement for Bug + Vince's read. Specifically check: am I wrong about any of the "NOT BUILT" entries in §6? If Aurexis already has a predicate that consumes germ coefficients, or if a sheaf composition has been demonstrated, the audit needs revision.

**Push back where I'm wrong.** That's how the audit becomes useful.
