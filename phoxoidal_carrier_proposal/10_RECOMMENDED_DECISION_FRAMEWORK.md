# 10 — Recommended Decision Framework

> **Not a decision. A framework for making one.** When would you adopt the v4 from-foundations rebuild? When would you keep AXP6 as-is? When would you do the v3 additive-layer approach instead? What evidence would update each direction? The discipline of this document is to be genuinely useful for "should we do this?" — not to be advocacy in framework clothing.

---

## 1. The four candidate decisions on the table

The handoff frames the decision as four-way (`README.md` §"What Bug should do after reading"):

| Option | What it means | Cost profile | Fits when |
|---|---|---|---|
| **A. Adopt** | Phase 1 builds the phoxoidal carrier; AXP6 keeps shipping in parallel for digital-file workflows | Highest cost (6-15 months, decoder is the long pole). Highest potential payoff. Largest architectural commitment. | Capture-mediated workflows are clearly on the deployment roadmap and the partners want to commit to substrate-level robustness. |
| **B. Redirect to v3** | Phase 1 builds the additive phoxoidal layer underneath AXP6 (per the v3 handoff). AXP6 stays the carrier substrate; the layer adds *some* capture-tolerance | Medium cost (lower than v4 but not zero). Smaller payoff (the diffeomorphism-invariance argument doesn't apply at full strength). Smaller commitment. | Capture-mediated workflows are exploratory; partners want to buy back some robustness without architectural transition. |
| **C. Reject and keep AXP6** | No Phase 1. AXP6 keeps shipping for its current workflows. The synthesis exercise was useful for what it revealed about both projects' substrates, even if it doesn't lead to new code | Zero new development cost. Zero payoff in the capture-mediated frontier. | The capture-mediated frontier is not on the deployment roadmap, OR the partners assess the costs in `08_HONEST_TRADEOFFS.md` as exceeding the expected benefit. |
| **D. Counter-propose** | The proposal made the architectural question visible enough that a *different* answer is now obvious to one or both partners. Author that answer | Cost-of-counter-proposal varies. Could be "actually, both projects should continue separately" (low cost) or "actually, here's a third architecture" (high cost). | The framing in this proposal is wrong but illuminates what the right framing is. |

The four are not mutually exclusive in time: a "Reject" today might become an "Adopt" later if the V2 frontier becomes real; a "Redirect to v3" might evolve into an "Adopt" later if v3 reaches its ceiling. The decision is for *now*, not forever.

## 2. The three load-bearing questions

The decision among A/B/C/D reduces to three questions whose answers are joint between the partners. The framework asks them in priority order.

### 2.1 Question 1 (workflow scope): is the V2 frontier real for the deployment roadmap?

**The architectural argument for v4 (`02_FAILURE_MODEL_ANALYSIS.md` §3) is conditional on this question's answer being yes.** If the deployment roadmap is "Vince emails Bug a PNG; Bug decodes; payload restored," AXP6 is the right substrate forever and the proposal is a beautiful answer to a question nobody is asking.

If the deployment roadmap includes "the carrier is captured by a phone camera, by a scanner, or via screen capture, and decode happens against the captured image rather than the original file," the V2 frontier is real and AXP6's pixel-grid substrate cannot defend it.

**Decision rule:**
- **Strong yes → v4 (Adopt) is the leading option.** The architectural transition is justified.
- **Mixed yes/no → v3 (Redirect) is the leading option.** Buy back some robustness without committing to architectural transition; revisit later if the capture frontier becomes more salient.
- **Strong no → Reject (C) is the leading option.** Don't spend engineering on a frontier that isn't on the roadmap.
- **Genuine uncertainty → Reject for now, revisit when the deployment roadmap is clearer.**

### 2.2 Question 2 (engineering budget): can the partners absorb the decoder research risk?

**The largest cost in `08_HONEST_TRADEOFFS.md` is the decoder (§3).** `06_DECODER_RESEARCH_PLAN.md` §4.6 estimates 6-9 months of focused single-engineer work for a captured-image roundtrip, with explicit go/no-go gates at the synthetic checkpoints.

This is not "1 weekend of fun coding." It is research-engineering with real failure modes. If the available engineering resource cannot absorb a 6-9 month commitment with an honest probability of mid-project re-planning, the proposal is overscoped for the available resource.

**Decision rule:**
- **Yes, the budget is there → v4 (Adopt) is feasible.** Plan with explicit go/no-go gates.
- **Partial budget → v3 (Redirect) might fit better.** The additive layer is a smaller engineering ask.
- **No budget → Reject (C) or C-with-revisit-later.** Don't start a decoder build that can't be finished.

### 2.3 Question 3 (architectural commitment): are the partners willing to swing big architecturally?

The handoff is explicit: "Bug and Vincent are aligned that finding the right architecture is more important than preserving any specific existing engineering." That alignment is required for v4 to be the right call.

If either partner is uncomfortable with the architectural transition — wants to preserve AXP6's deployment lineage, wants to avoid IP/authorship complications, wants to keep the projects' identities distinct rather than composing them, etc. — v4 is the wrong call regardless of the other two questions' answers. The partners don't have to want this.

**Decision rule:**
- **Both partners willing → v4 (Adopt) on the architectural front.** Move on to questions 1 and 2.
- **One partner willing, one cautious → v3 (Redirect) is the compromise.** Smaller commitment lets cautious partner observe before committing further.
- **Both partners cautious → Reject (C). Both projects continue separately. The synthesis still happened; it informs both projects' future work even if no joint code is written.**

## 3. Composed decision matrix

Combining the three questions:

| Q1 (V2 frontier real?) | Q2 (decoder budget?) | Q3 (architectural willingness?) | Recommended decision |
|---|---|---|---|
| **Yes** | **Yes** | **Yes** | **A. Adopt v4.** All three lights green. |
| Yes | Yes | Mixed/cautious | **B. Redirect to v3.** Architecturally cautious; v3 lets the partners get robustness benefit without composition commitment. |
| Yes | Partial | Yes | **B. Redirect to v3.** Engineering budget can't sustain v4's research risk. |
| Yes | Partial | Cautious | **B. Redirect to v3.** Both other constraints push toward smaller swing. |
| Yes | No | Any | **C. Reject for now.** Can't build it; revisit when budget exists. |
| Mixed | Yes | Yes | **B. Redirect to v3.** Workflow uncertainty makes v4's commitment premature. |
| Mixed | Yes | Mixed/cautious | **B. Redirect or C.** Workflow + architecture both uncertain → smallest move. |
| Mixed | Partial/No | Any | **C. Reject for now.** Workflow uncertainty + budget constraint → defer. |
| No | Any | Any | **C. Reject.** Architectural transition for an unrealized workflow is overkill. AXP6 is the right substrate. |
| Any | Any | Any (counter-proposal arises) | **D. Counter-propose.** If reading the proposal makes a different right answer obvious, author it. |

Note: this matrix is a recommendation framework, not a deterministic algorithm. The partners can override based on factors not captured in three axes (commercial considerations, third-party requirements, learning value of doing v4 even at high cost, etc.). The matrix exists to make the *default* decision explicit so overrides are visible as overrides.

## 4. Evidence that would update each direction

If a decision is made and later evidence surfaces that contradicts the assumptions the decision was made on, the partners should re-open. The framework names what evidence updates what direction:

### 4.1 Evidence that would push toward A (Adopt v4) from B or C

- A real-world capture-mediated workflow becomes commercially valuable.
- A decoder feasibility spike (subset of `06_DECODER_RESEARCH_PLAN.md`'s detection + germ-fit work) succeeds beyond expectations on synthetic data.
- v3 (additive layer) reaches its robustness ceiling and visibly under-delivers in the V2 frontier.
- A funding source or engineering resource becomes available that absorbs the decoder budget risk.
- An external request explicitly asks for capture-mediated robustness (a customer, a research collaborator, a regulatory requirement).

### 4.2 Evidence that would push toward B (Redirect to v3) from A or C

- The decoder feasibility spike reveals harder-than-expected failure modes that v3 sidesteps.
- The capture-mediated frontier turns out to be narrower than thought (e.g., V2 protocol envelope is sufficient for all real deployments — pre-decode geometric correction works well enough).
- IP/authorship terms (`09_OPEN_QUESTIONS.md` §5) prove harder to settle than the engineering, suggesting smaller architectural commitment.
- Engineering budget shrinks below what v4 requires but stays above v3's lower bar.

### 4.3 Evidence that would push toward C (Reject) from A or B

- Capture-mediated workflows fail to materialize on the deployment roadmap.
- Decoder feasibility spike reveals the architecture is harder to realize than `06` estimates suggest.
- The 1.5-3× density penalty (`05_INFORMATION_DENSITY_ANALYSIS.md` §2.6) turns out to be unacceptable for the typical workflows.
- v3 ships and is sufficient (or nearly sufficient) for the actual deployment regime, so v4's architectural transition stops being justifiable.
- A different architectural option (D — counter-proposal) becomes more attractive than either v4 or v3.

### 4.4 Evidence that would push toward D (Counter-propose)

- The act of reading the proposal makes the partners realize the right architecture is something neither v4 nor v3 — for example: "the carrier should be a CRYPSOID-rendered scene without any payload germs at all, just relying on the natural-image's own catastrophe structure as the carrier" (this is a real possibility worth flagging if it occurs to either partner).
- A third project, technique, or substrate is identified that the proposal didn't consider.
- The partners agree that the right answer is "neither composition; both projects continue separately" and the counter-proposal is "no joint architecture, but the synthesis informs both projects' independent roadmaps."

## 5. Time-of-decision considerations

### 5.1 The decision does not have to be made in one session

The handoff specifies joint review, not joint same-day decision. The proposal package is sized to be readable in a half-day; making the decision well may benefit from time between reading and deciding. Partners should explicitly schedule:

- Solo read time (each partner reads independently, takes notes).
- One or more joint discussion sessions.
- Time for follow-up questions to be authored (this proposal will not have anticipated every question).
- A specific decision deadline that respects the work but is not artificially urgent.

### 5.2 Some questions can be deferred even after a tentative decision

Per `09_OPEN_QUESTIONS.md` checklist, several questions don't need to resolve before adoption:
- Naming (§3) can wait until Phase 1 has a working artifact to attach a name to.
- Disclosure / watermark policy (§10) can be a Phase 1 deliverable.
- Some others.

Other questions *must* resolve before adoption:
- IP / authorship terms (§5) — don't write code under unresolved terms.
- Target capture envelope (§2) — Phase 1 cannot start without knowing what it's targeting.
- Lane choice (§8) — affects where the working tree lands.

The partners should agree which of `09_OPEN_QUESTIONS.md`'s items are blocking and which are deferrable.

### 5.3 An "Adopt" decision benefits from a budgeted pre-Phase-1 spike

If the partners adopt v4, the highest-leverage de-risking move before full Phase 1 commitment is a **2-3 week scoping spike** that does:

- Stand up a synthetic encoder (germ placement only, no Tier C, no manifest cluster).
- Stand up a synthetic decoder (scale-space detection + inverted germ-fit only, no persistent homology, no Mumford-Shah).
- Roundtrip a small synthetic carrier (~1000 germs, no capture noise) and measure: detection rate, classification accuracy, end-to-end SHA-256 success.

If the spike's metrics are within an order of magnitude of what's needed for the full architecture, the partners commit to full Phase 1. If the metrics are off by orders of magnitude, the partners replan (often: re-open the v4-vs-v3 decision in light of empirical evidence about decoder difficulty).

This spike is not in `07_INTEGRATION_BRIDGES.md` because it sits before Phase 1 in the sense of "should we start Phase 1 at all?" — it is a meta-Phase-0.5 step the partners may want to authorize as a short follow-on to this Phase 0 package, separate from full Phase 1 commitment.

## 6. The honest meta-recommendation

This document is not the proposal advocating for itself. It tries to be the framework that lets either decision (Adopt or Reject) be made on the merits. Two honest meta-observations the framework doesn't bury:

### 6.1 The proposal is not risk-free

`08_HONEST_TRADEOFFS.md` enumerates 15 substantive costs. The decoder is a real research risk. The density penalty is real. The composition has IP and provenance complications. A reader who comes away thinking the proposal is risk-free has been misled by the writing; the writing tries hard not to mislead.

### 6.2 The proposal is not pointless even if rejected

The synthesis exercise — making both projects' overlap with each other and with Thom's semiophysics tradition explicit — is itself valuable to both projects independently of whether the joint architecture ships. If the partners reject, both projects walk away with sharper understanding of their own substrates and their own roadmaps. The Phase 0 work was the cost of making that understanding visible. That cost is sunk; the value persists.

The architecturally wrong choice would be to adopt v4 because the proposal is well-written rather than because Q1, Q2, Q3 (above) all answer yes. Equally, the architecturally wrong choice would be to reject v4 because the writing is intimidating rather than because the questions answer in ways that don't justify the swing. The framework above is built to keep the decision on the questions, not on the writing.

---

## 7. The framework as a checklist

For partners who prefer a checklist over a matrix:

```
[ ] Question 1: Is the V2 frontier (capture-mediated workflows) on our deployment roadmap?
    [ ] Strong yes
    [ ] Mixed
    [ ] Strong no

[ ] Question 2: Can we absorb 6-9 months of focused decoder engineering with go/no-go gates?
    [ ] Yes, full budget
    [ ] Partial budget (could do v3-scale work)
    [ ] No budget

[ ] Question 3: Are both partners willing to commit to architectural composition of CRYPSOID + Aurexis Core?
    [ ] Both willing
    [ ] One willing, one cautious
    [ ] Both cautious

[ ] Apply the matrix in §3 to derive the recommended decision.

[ ] Override the matrix only with explicit reasoning (note the override in writing).

[ ] Resolve the blocking items from `09_OPEN_QUESTIONS.md` checklist (§5 IP terms, §2 capture envelope, §8 lane choice).

[ ] If decision is Adopt: authorize the 2-3 week scoping spike from §5.3 before full Phase 1.

[ ] If decision is Redirect: re-read the v3 handoff and re-scope its Phase 1.

[ ] If decision is Reject: agree on what (if anything) the synthesis informs in each project's independent roadmap.

[ ] If decision is Counter-propose: author the counter-proposal as the next Phase 0 cycle.

[ ] Schedule the decision-revisit point: 6 months from decision date is a reasonable cadence.
```

---

**Cross-references.** The proposal being decided on is in `03_PHOXOIDAL_CARRIER_ARCHITECTURE.md`. The honest costs to weigh are in `08_HONEST_TRADEOFFS.md`. The questions whose answers feed this framework are in `09_OPEN_QUESTIONS.md`. The decoder research that drives Question 2 is in `06_DECODER_RESEARCH_PLAN.md`.
