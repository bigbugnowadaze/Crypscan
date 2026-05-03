# 09 — Open Questions for Bug and Vince

> Joint open questions raised by the proposal that require partner-level decisions before Phase 1 can begin. Each question states what's at stake, what the proposal currently assumes, and what would change if the assumption were wrong.

---

## 1. Is "supersede AXP6 as the carrier" actually wanted, or is the additive approach (v3 handoff) preferred for risk management?

**At stake:** The whole architectural posture of the proposal.

**The proposal currently assumes:** the from-foundations rebuild (v4) is the right move because the V2 frontier is capture-mediated and pixel-grid encodings can't fully close that gap with more redundancy (`02_FAILURE_MODEL_ANALYSIS.md` §3).

**If wrong:** The v3 additive-layer approach — phoxoidal layer underneath AXP6, with AXP6 still doing the core carrier work — buys back some robustness with much less architectural commitment. v3 is a smaller swing that fails more gracefully if the diffeomorphism-invariance argument doesn't pan out empirically. The partners agreed at the start that finding the right architecture is more important than preserving any specific existing engineering — this includes preserving the v4 framing if it's wrong.

**Suggested decision criterion:** If the partners are confident the V2 frontier (capture-mediated workflows) is on the deployment roadmap and matters commercially, v4 is the right swing. If the V2 frontier is speculative or distant, v3 is the right hedge. `10_RECOMMENDED_DECISION_FRAMEWORK.md` §3 expands on this.

## 2. Which capture envelope is the proposal actually targeting?

**At stake:** The decoder's working envelope and Phase 1 success criteria.

**The proposal currently assumes:** the V2 capture protocol's envelope (`V2_CAPTURE_PROTOCOL.md`: handheld Galaxy S23 Ultra at chosen baseline distance, MSI G27C4X monitor, indoor home-office lighting, declared session window). The proposal claims diffeomorphism invariance robustness inside this envelope and degradation outside it.

**If wrong:** Two possible failures:
- **Envelope is too narrow.** If the deployment use case requires capture in low light, off-axis, or in motion, the V2 protocol's success doesn't carry over and Phase 1 needs a wider capture protocol (which doesn't exist yet — V2-M7 is the "controlled expansion" gate per `V2_ROADMAP.md` lines 102–110, currently open).
- **Envelope is too wide.** If the deployment use case is even more constrained (lab-grade fixed mount, lab lighting), pre-decode geometric correction (`02_FAILURE_MODEL_ANALYSIS.md` §3.3 Option A) might suffice and the architectural transition is overkill.

**Suggested decision criterion:** Bug and Vince should jointly name the target capture envelope before Phase 1 starts. Existing V2 protocol is the conservative default; documenting any wider or narrower envelope as the actual target avoids building for the wrong regime.

## 3. Naming the new format / extension

**At stake:** Public-facing identity and developer recognizability.

**The proposal currently assumes (placeholder):**
- Lane name: "phoxoidal carrier" or "PhoxCar"
- Format magic: `CRYPSOID_3DPHOX_VCAR_PHOXOIDAL_CARRIER`
- File extension: `.phoxcar.png` or similar
- Inner header magic: keep `AXP6` (preserves AXP6 brand and the working-decoder lineage) OR rename to a phoxoidal-specific magic like `PHOX` or similar.

**If wrong:** Naming choices have downstream consequences for marketing, search, and developer adoption. Bug and Vince might want to brand differently than either existing project. The handoff explicitly leaves this open ("`phoxoidal-carrier` (placeholder — naming is open)").

**Suggested decision criterion:** Bug and Vince agree the name jointly. Suggest waiting until Phase 1 is past the synthetic-roundtrip gate so the name attaches to a working artifact rather than a paper architecture.

## 4. If the phoxoidal carrier ships, does AXP6 stay as an alternate substrate or get formally deprecated?

**At stake:** AXP6 users' stability and the long-term substrate strategy.

**The proposal currently assumes:** AXP6 stays. Per `Hard Rules` §4 in the package's `README.md` (taken from the v4 handoff): "AXP6 is not deleted. It continues to ship for digital file→file workflows where it works perfectly. The phoxoidal carrier is a parallel substrate optimized for capture-mediated workflows. Both can coexist."

**If wrong:** Two possible failures:
- **Maintaining two substrates is too costly.** If the engineering budget can't sustain both indefinitely, the partners might prefer a deprecation timeline for AXP6 once the phoxoidal carrier matures.
- **AXP6 should be the only substrate for some use cases.** If AXP6's density advantage matters enough, the partners might deliberately keep AXP6 as the recommended substrate for digital-file-only workflows, with the phoxoidal carrier explicitly recommended only for capture-mediated workflows. This is the proposal's current framing but needs explicit endorsement.

**Suggested decision criterion:** The partners should jointly write a substrate-selection decision tree for end users. "Digital file in, digital file out → AXP6. Digital file in, captured-image out → phoxoidal carrier." Make the choice explicit and documented so users don't have to guess.

## 5. IP / authorship terms

**At stake:** Legal and economic ownership of the composed result.

**The proposal currently assumes:** TBD between partners. Per the handoff §"Hard rules" #6: "CRYPSOID is Bug's. Aurexis Core is Vince's. The composition produces a clearly-attributed result. Terms TBD between partners."

**If wrong:** The composition produces something neither owns alone. Without explicit terms, downstream questions become fraught:
- Who can ship the composed result commercially?
- Who controls future versions?
- What happens if the partnership changes?
- Can either project ship a fork that incorporates the composed result?
- How are revenues, if any, divided?
- How do existing licenses on each project's code propagate to the composition?

**Suggested decision criterion:** Set terms before Phase 1 starts. Phase 0 produces an architecture; Phase 1 produces actual code that has IP implications. Don't write code under unresolved terms.

## 6. Acceptable density penalty vs AXP6

**At stake:** A hard threshold for the proposal's economic viability in deployments where data density matters.

**The proposal currently assumes (no commitment):** the 1.5-3× density penalty for typical payloads is acceptable, and the up-to-10× penalty for incompressible worst-case payloads is acceptable for capture-mediated workflows where AXP6 doesn't work at all.

**If wrong:** Three possible failures:
- **Even 1.5× is too much.** If the deployment requires payload density at AXP6 levels for typical payloads, the architecture needs different bit-budget choices or a different germ basis (`03_PHOXOIDAL_CARRIER_ARCHITECTURE.md` §6 option 3 on VSA might help) or the architecture isn't a fit.
- **Up to 10× is too much.** Even for capture-mediated workflows, if incompressible-payload deployments are common, the worst-case density penalty is a deal-breaker.
- **The acceptable threshold is workflow-specific.** Each deployment use case might have its own threshold and the proposal needs to be designed with parameter knobs that let the operator pick.

**Suggested decision criterion:** Bug and Vince name a threshold (e.g., "≤ 3× density penalty for typical payloads, ≤ 5× for worst-case incompressible payloads, measured on representative sample workloads") that Phase 1 must hit. Be explicit; "as low as possible" is not a threshold.

## 7. Temporal extension — does video matter?

**At stake:** Whether the architecture should anticipate video-frame carriers or stay static-only for V1.

**The proposal currently assumes:** static-image carrier first, with `03_PHOXOIDAL_CARRIER_ARCHITECTURE.md` §8.3 noting that "video frames" are a natural extension. The cost of supporting video is non-trivial (temporal redundancy across frames, frame-fusion in the decoder, motion compensation). Aurexis Core's V2 charter is explicitly static-first ("static-first — no motion, no video pipelines, no live tracking dependencies" — `V2_CHARTER.md` line 23).

**If wrong:** If video deployments matter commercially, the architecture should anticipate them in the format spec rather than retrofit them later. The germ-coordinate-system question (do germs live in scene-space or world-space across frames?) is meaningfully different for video.

**Suggested decision criterion:** Static-only for V1 is the right answer; explicit "video is a Phase 2+ extension" is the right framing. But if Bug or Vince already have deployment use cases where video matters, that should change Phase 1's format-spec design.

## 8. Which research lane does this work live in?

**At stake:** Where the working tree lands, which capstones it produces, which existing branches it composes with.

**The proposal currently assumes:** A new "V3 phoxoidal carrier" research lane parallel to V2 (`07_INTEGRATION_BRIDGES.md` §1). Alternative: as a charter amendment to V2 (analogous to V2-D0 through V2-D4, the Decode Engine Track per `V2_CHARTER_AMENDMENTS.md`).

**If wrong:** Lane choice has real consequences:
- **Inside V2:** the work inherits V2's charter constraints, V2's milestone gates, V2's release timing. Pro: existing integration with V2 infrastructure. Con: V2's static-first / one-phone-first constraints may conflict with the phoxoidal lane's needs.
- **In a new V3 lane:** the work has its own charter and gate ladder. Pro: design freedom. Con: more administrative overhead; another lane to maintain alongside V1 (frozen) and V2.
- **Inside `07_VISION_SUBSTRATE/`:** Aurexis Core's existing vision-substrate area might be the natural home, especially if Branch 4's "View-Dependent Markers / 3D Moment Invariants" composition is the load-bearing one.

**Suggested decision criterion:** Vincent's call. He owns Aurexis Core; the lane structure is his architectural prerogative. The proposal can re-home easily either way.

## 9. Encoder-side germ-placement optimization — is this a research lane or just engineering?

**At stake:** Phase 1 budget for encoder development.

**The proposal currently assumes:** encoder germ-placement is "real research-engineering work — probably the largest single chunk of new code" (handoff §"Encoder work"). `08_HONEST_TRADEOFFS.md` §2 estimates 6-10 weeks for a first version.

**If wrong:** If the encoder requires substantial new optimization research (not just engineering composition of existing techniques), the timeline blows out. There are open research questions: What's the right loss function for the placement? Can it be solved greedily, or does it need a global optimizer? How does the encoder handle Tier C field constraints in tractable time?

**Suggested decision criterion:** Phase 1 should explicitly include a 2-3 week scoping spike for the encoder problem before committing to the full encoder build estimate. If the spike reveals substantial research needs, replan.

## 10. Disclosure / provenance for steganographic carriers that look benign

**At stake:** Trust-and-safety posture for the proposed carrier.

**The proposal currently assumes:** This is out of scope for Phase 0 architecture but flagged in `08_HONEST_TRADEOFFS.md` §4 as a real responsibility. The proposal does not yet specify whether the carrier should include a structural watermark identifying it as a phoxoidal carrier, or whether some carriers should require disclosure to viewers.

**If wrong:** Two failure modes:
- **No disclosure mechanism, no watermark.** Bad actors can use the carrier to smuggle payload without viewers' awareness. This may run into platform policies (image-hosting services, content moderation) or jurisdictional rules.
- **Mandatory watermark or disclosure.** Limits legitimate use cases (e.g., aesthetic carriers where the data layer is part of the design vs visible disclosure); creates a new vector for adversaries to detect and strip.

**Suggested decision criterion:** Bug and Vince decide jointly whether the format spec should include an optional "disclosed-carrier" mode, a mandatory watermark, or neither. This is a values decision, not a technical one.

## 11. Compatibility with future format extensions (CRYPSOID v0.4, v32, v33, v34, v40+)

**At stake:** The proposed `.3dphox` extension's interaction with CRYPSOID's own roadmap.

**The proposal currently assumes:** the phoxoidal carrier sits in CRYPSOID's `CRYPSOID40\0` magic family or a parallel `VCAR` magic. CRYPSOID's roadmap (`docs/ROADMAP.md` §"Phase D.4") includes v31 (graph + edges + delta), v32 (lighting), v33 (materials), v34 (temporal), and v40+ (caustics/glass) — all of which evolve `.3dphox`.

**If wrong:** If CRYPSOID's format evolution and the phoxoidal carrier's format requirements diverge, future versions become harder to compose. Conversely, if the proposal can take advantage of v32 (lighting) to encode germs in shadow patterns, or v34 (temporal) for video carriers, the architecture has more design surface than this proposal contemplates.

**Suggested decision criterion:** Bug owns CRYPSOID's format. The proposal should explicitly defer format-evolution coordination to Bug and accept that the phoxoidal carrier's format may need to move with CRYPSOID's, not against it.

## 12. Phase 0 stop point — is the proposal package as authored sufficient for the decision?

**At stake:** Whether more proposal authoring should happen before the decision is made.

**The proposal currently assumes:** the twelve deliverables in this package are sufficient for Bug and Vince to evaluate the architectural question. Per the handoff §"Stop here": "After Phase 0, **stop**. Do not propose Phase 1 contents in detail. Bug and Vince need to read the package, evaluate jointly, and decide."

**If wrong:** If the proposal package is missing something — a specific scenario worked end-to-end, a more rigorous diffeomorphism-invariance proof, a concrete encoder design, an actual benchmark on captured images — the partners may need additional Phase 0 work before they can decide.

**Suggested decision criterion:** Bug and Vince should jointly say "this proposal package is sufficient to decide" or "we need X more before we can decide." If the latter, X gets named explicitly and Phase 0 continues until X is delivered.

---

**Decision-readiness checklist for the partners.** Before joint decision, both partners should agree they have a position on each of:

- [ ] §1 (v4 vs v3 architecture)
- [ ] §2 (target capture envelope)
- [ ] §3 (naming) — can defer until Phase 1 if undecided now
- [ ] §4 (AXP6 deprecation strategy)
- [ ] §5 (IP / authorship terms) — must resolve before Phase 1
- [ ] §6 (acceptable density penalty)
- [ ] §7 (video extension priority)
- [ ] §8 (which research lane)
- [ ] §9 (encoder-side scoping)
- [ ] §10 (disclosure / watermark policy) — can defer until Phase 1 if undecided now
- [ ] §11 (CRYPSOID format coordination)
- [ ] §12 (whether the proposal package is sufficient)

The decisions don't all have to happen in one session, but they should all happen before the proposal is adopted (or before each Phase 1 milestone needs them, whichever is earlier).

---

**Cross-references.** The decision framework that uses these questions is in `10_RECOMMENDED_DECISION_FRAMEWORK.md`. The architectural assumptions each question challenges are in `03_PHOXOIDAL_CARRIER_ARCHITECTURE.md`. The honest tradeoffs each question helps the partners weigh are in `08_HONEST_TRADEOFFS.md`.
