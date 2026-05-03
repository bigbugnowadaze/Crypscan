# Phoxoidal Carrier — Phase 0 Architectural Proposal Package

**Owners:** Bug (CRYPSOID) + Vincent Anderson (Aurexis Core / AXP6) — full partnership
**Cowork pass:** Phase 0 (proposal authoring only)
**Date authored:** May 2026
**Working name for the new substrate:** `phoxoidal-carrier` (placeholder; naming is open — see `09_OPEN_QUESTIONS.md` §3)
**Supersedes handoff:** v3 (additive auxiliary layer); see §"Relationship to v3" below
**Status of this package:** awaiting joint Bug+Vince review

---

## What this package is

Phase 0 of the v5 cowork handoff (`cowork_handoff_v4_phoxoidal_carrier_redesign.md`). The handoff asked for an architectural proposal — not an implementation, not a sales pitch — that Bug and Vince can read jointly and then decide whether to:

1. **Adopt** the from-foundations rebuild this package proposes,
2. **Redirect** to the v3 additive-layer approach,
3. **Reject** the proposal and keep AXP6 as-is, or
4. **Counter-propose** something this package's framing makes visible.

The package does not predetermine that decision. It exists to inform it.

## What this package proposes (one-paragraph version)

Replace AXP6's pixel-grid carrier substrate with a **phoxoidal field** rendered from a CRYPSOID `.3dphox` scene. Payload bits are encoded as catastrophe-germ coefficients (Pearcey-class κ₁/κ₂/χ/ω/ζ — five real numbers per germ), placed in a 3D scene, rendered to 2D for display. The decoder is a **catastrophe-germ extractor** that recovers structure (not pixels) from a captured image. Diffeomorphism invariance — a theorem from catastrophe theory — guarantees germ classification survives smooth coordinate transformations of the captured image plane (perspective tilt, rolling shutter, focus blur, lens warp, moiré). AXP6's payload-integrity contracts (Brotli + SHA-256 + bit-exact verification) are preserved as outer wrappers around the new carrier; they were never the architectural problem.

## The twelve deliverables in this package

| # | File | What it does |
|---|---|---|
|   | [`README.md`](README.md) | This cover note |
| 0 | [`00_CONVERGENCE_AND_HISTORY.md`](00_CONVERGENCE_AND_HISTORY.md) | How CRYPSOID and Aurexis Core converged independently; the Thom semiophysics lineage; why this proposal exists |
| 1 | [`01_AXP6_ARCHITECTURE_DIGEST.md`](01_AXP6_ARCHITECTURE_DIGEST.md) | Verified-against-source description of AXP6 from `aurexis_decode.py`, with line citations |
| 2 | [`02_FAILURE_MODEL_ANALYSIS.md`](02_FAILURE_MODEL_ANALYSIS.md) | What AXP6 defends against, what it doesn't, why pixel-grid encodings cannot fully close the V2 gap with more redundancy |
| 3 | [`03_PHOXOIDAL_CARRIER_ARCHITECTURE.md`](03_PHOXOIDAL_CARRIER_ARCHITECTURE.md) | The proposed architecture in full |
| 4 | [`04_DIFFEOMORPHISM_INVARIANCE_ARGUMENT.md`](04_DIFFEOMORPHISM_INVARIANCE_ARGUMENT.md) | The mathematical case — what the math gives, what it does not |
| 5 | [`05_INFORMATION_DENSITY_ANALYSIS.md`](05_INFORMATION_DENSITY_ANALYSIS.md) | Back-of-envelope bits-per-area numbers vs the AXP6 sample carrier |
| 6 | [`06_DECODER_RESEARCH_PLAN.md`](06_DECODER_RESEARCH_PLAN.md) | The catastrophe-germ extraction problem, toolbox candidates, riskiest unknowns |
| 7 | [`07_INTEGRATION_BRIDGES.md`](07_INTEGRATION_BRIDGES.md) | Proposed bridge milestones in Aurexis Core's bridge-and-capstone format |
| 8 | [`08_HONEST_TRADEOFFS.md`](08_HONEST_TRADEOFFS.md) | Single doc collecting every "this is harder than it sounds" point |
| 9 | [`09_OPEN_QUESTIONS.md`](09_OPEN_QUESTIONS.md) | Joint open questions for Bug and Vince |
| 10 | [`10_RECOMMENDED_DECISION_FRAMEWORK.md`](10_RECOMMENDED_DECISION_FRAMEWORK.md) | Framework for making the decision (not the decision itself) |

`refs/` contains pointers to the source repositories the package was authored against. Nothing in `refs/` is redistributed source — it is a path index for the reviewer.

## Reading order

If you have one hour: README → 03 → 02 → 08 → 10.
If you have a half-day: 00 → 01 → 02 → 03 → 04 → 05 → 06 → 07 → 08 → 09 → 10.
If you have an open block: read in numbered order. Each doc cites prior docs by section number.

## Hard rules carried over from the handoff

These are not negotiable and inform every doc in this package:

1. Aurexis Core's gate-tracking discipline applies absolutely.
2. CRYPSOID's no-GPU rule applies absolutely (numpy + scipy + Pillow + ffmpeg + new persistent-homology library; no torch, no cuda).
3. Aurexis Core's frozen V1 surface (ACOR-1.1, all 33 tags, all 26 backup branches, the locked release zip) is untouchable.
4. AXP6 is not deleted. It continues to ship for digital file→file workflows where it works perfectly.
5. Bit-exact contracts preserved (Brotli + SHA-256 + byte-identity decode).
6. Provenance and IP discipline. CRYPSOID is Bug's. Aurexis Core is Vince's. The composition produces a clearly-attributed result; terms TBD.
7. Phased reviewable artifacts. Phase 0 produces a proposal. Joint review. Phase 1+ contingent on sign-off.

## Relationship to v3 (the additive-layer handoff)

The v3 handoff proposed a phoxoidal layer *underneath* AXP6. v4 (the source for this package) reframes it as a from-foundations replacement of the carrier substrate while preserving AXP6's payload-integrity contracts. v3 is not deleted; it is the leading "if this v4 proposal is rejected" fallback — a smaller, lower-risk move that buys back some of the same robustness without the architectural commitment. `10_RECOMMENDED_DECISION_FRAMEWORK.md` §3 names the conditions under which v3 is the better answer.

## Material status (what was loaded vs not loaded for Phase 0)

- ✓ `aurexis_decode.py` (737 lines) — read in full; cited line-by-line in `01_AXP6_ARCHITECTURE_DIGEST.md`.
- ✓ `DECODE_GUIDE.md` — read in full.
- ✓ CRYPSOID repo (`https://github.com/bigbugnowadaze/CRYPSOID`) — full clone read for `docs/FORMAT.md`, `docs/crypsorender_architecture.md`, `docs/thesis_digest.md`, `docs/ROADMAP.md`, `reports/TIER_1_results.md`, `reports/PROJECT_STATE.md`, `tools/crypsorender/math/germ.py`. Cited throughout.
- ✓ Aurexis Core repo (`https://github.com/KungFury87/Aurexis`) — full clone read for `README.md`, `CORE_TREE_MAP.md`, `V2_CHARTER.md`, `V2_ROADMAP.md`, `V2_CAPTURE_PROTOCOL.md`, `V2_PILOT_RUNBOOK.md`, `V2_MILESTONE_GATES.md`, `00_PROJECT_CORE/HIGHER_ORDER_COHERENCE_BRANCH_CAPSTONE_V1.md`, `00_PROJECT_CORE/CAPTURE_TOLERANCE_BRIDGE_V1_GATE_VERIFICATION.md`, `06_PROOF_SYSTEM/aurexis_research_sim/README.md`. Cited throughout.
- ⚠ `sample-2.mp4.axp6.png` (the 30 MB payload encoded as an 11032×13120 PNG) — **not loaded for Phase 0**. Phase 0 is proposal authoring sourced from the `aurexis_decode.py` source code; the sample carrier is needed for Phase 1 roundtrip benchmarking, not for the digest. The handoff's stated dimensions are honored verbatim wherever cited.

## What Bug should do after reading

1. Read all twelve docs.
2. Especially scrutinize: `01_AXP6_ARCHITECTURE_DIGEST.md` (must be source-accurate), `04_DIFFEOMORPHISM_INVARIANCE_ARGUMENT.md` (must claim only what the math gives), `08_HONEST_TRADEOFFS.md` (must actually be honest — if it sounds risk-free, the writing has failed).
3. Schedule a joint review with Vince.
4. Use `10_RECOMMENDED_DECISION_FRAMEWORK.md`. Possible outcomes: adopt, redirect to v3, reject and keep AXP6, counter-propose.

The decision is joint. This package exists to inform it, not to predetermine it.

## Stop point

Phase 0 ends here. Do not begin Phase 1 (encoder/decoder/benchmark feasibility build) until both partners have signed off and named the next phase explicitly.

---

*Authored under the v4/v5 cowork handoff. The proposal swings at the architectural level. Whether to adopt it is a joint decision for Bug and Vince after Phase 0 ships.*
