# Addendum 05 — Aurexis Prior-Work Audit (post-spike-9A)

**Status:** honest-diligence audit; informs spike-9B framing
**Authored:** 2026-05-04
**Trigger:** Bug's question — "look at the aurexis repo and analyze the
documents to determine how much of this has already been tried."
**Scope:** survey of `/tmp/Aurexis/` for prior work that overlaps with
the phoxoidal-carrier proposal, spike-8B (real-capture validation),
ADDENDUM_04 (prior-art research), and spike-9A (synthetic channel +
discrete substrate variant).

## Headline

**A lot has been tried.** The Aurexis Core repo already contains:

1. A **locked V2 capture protocol** (`V2-CAP-PROTO-1.0-LOCK`, 2026-04-14)
   with explicit equipment (S23 Ultra + MSI G27C4X), procedure, lighting,
   and rig requirements. Bug's spike-8B used **different equipment**
   (S21 FE + Asus laptop) — outside the locked protocol.
2. A **locked benchmark artifact set** (`V2-BENCH-B1`, 2026-04-14) with
   5 mandatory test artifacts including `b1-corners-fiducials.png` (the
   geometric-baseline analog of our reference_carrier.png).
3. An **existing real-capture pipeline** (`run_real_capture_pipeline.py`)
   that processes phone photos/videos and runs Gate 3 evaluation. Bug's
   spike-8B `analyze.py` partially duplicates this.
4. **An already-working production-discrete-substrate**: **Aurexis E/D
   V2.1**, demonstrated **byte-exact real capture** of **3,568 bytes**
   through S23 Ultra → APK → MSI monitor, **2026-04-17** — a month before
   spike-8B. This format uses 128×128 discrete modules × 4 colors with
   RS(255,223) + Chase-2 soft-decision decoding.
5. **Deep cross-domain research** (`RESEARCH_deep_cross_domain.md`,
   2026-04-18) covering 30 ranked techniques across coding theory,
   metrology, fiducial systems, color science, sheaf theory, HDC/VSA, and
   screen-camera communication. This **substantially overlaps with**
   ADDENDUM_04 and **predates it**.
6. A **separate Phoxelis (.phox) format** (`phox_format.py`) that
   encodes "predicate states over a cell grid" — yet another discrete
   substrate, not the same as our continuous-catastrophe-germ approach.
   Round 37c v0.4 demonstrated **2,048 bytes PNG byte-exact** but **0
   bytes through JPEG q=75** (same screen-shooting failure mode we
   discovered in spike-8B).

## Honest mapping: phoxoidal-carrier work vs Aurexis prior work

| Our work | Aurexis prior work | Overlap? |
|---|---|---|
| `phoxoidal_carrier_proposal/` (catastrophe-germ continuous substrate) | None — Aurexis uses discrete modules / predicate cells | **Genuinely novel** |
| spike-8B capture protocol (`CAPTURE_PROTOCOL.md`) | `V2_CAPTURE_PROTOCOL.md` (locked V1.0) | **Duplicated.** Aurexis's protocol is more rigorous (locked equipment, lighting state declared, session manifest, etc.) |
| spike-8B reference_carrier.png | `V2_BENCHMARK_SET/assets/b1-*.png` (5 locked artifacts) | **Duplicated.** Aurexis has 5 mandatory test artifacts; we used 1 |
| spike-8B `analyze.py` + `report.py` | `run_real_capture_pipeline.py` + Gate 3 evaluation | **Duplicated.** Aurexis's pipeline is more developed (concurrent processing, Gate 3 ledger, full evidence reporting) |
| ADDENDUM_04 prior-art survey (StegaStamp, Light Field Messaging, Fang, etc.) | `RESEARCH_deep_cross_domain.md` (30 ranked techniques, 2026-04-18) | **Substantially duplicated.** Aurexis's survey is broader and earlier; ours adds specific 2020-2025 deep-learning-based screen-camera literature |
| spike-9A synthetic distortion harness | unknown — couldn't find equivalent in Aurexis | **Genuinely new** (worth committing) |
| spike-9A 16-symbol discrete classifier finding | Aurexis E/D V2.1 already uses discrete modules + RS+Chase decoding, **with empirical real-capture success** | "Discovery" was already known; the **specific catastrophe-germ-aesthetic variant** is new |

## What this means

The phoxoidal-carrier proposal is genuinely novel as a substrate (the
continuous catastrophe-germ basis is unique), but several of the
**downstream** insights spike-8B and spike-9A produced — that
discrete-symbol substrates beat continuous ones for screen-camera, that
real-capture validation requires careful protocol, that prior art
already studied the channel — were already in Aurexis's working tree.

**Several spike-pieces are duplicate work.** Specifically:
- The capture protocol should reference and align with `V2_CAPTURE_PROTOCOL.md`
  rather than independently re-inventing equipment + lighting requirements.
- The benchmark set should include or alias the V2-BENCH-B1 artifacts
  (especially `b1-corners-fiducials` for pose-only validation) rather
  than only test against one custom carrier.
- The real-capture pipeline could be a thin wrapper over (or contribution
  to) `run_real_capture_pipeline.py`, not a parallel implementation.
- ADDENDUM_04 should reference `RESEARCH_deep_cross_domain.md` directly
  and treat it as the primary survey; ADDENDUM_04's contribution is
  the specific 2020-2025 deep-learning screen-camera literature
  (StegaStamp, LFM, Fang follow-ups) that Aurexis's research
  predated.

**Aurexis E/D V2.1 already passes the real-capture test we have not.**
Real-capture byte-exact on 2026-04-17. Different format (discrete colored
modules + RS+Chase), but proves the screen-camera channel is
*solvable* — which we hadn't yet demonstrated for any substrate of ours.

## Implications for spike-9B

The spike-9A recommendation to build a complete 16-nibble-pair codec and
re-run capture on real hardware is **still valid** — but should be
**reframed**:

1. **Use Aurexis's V2-CAP-PROTO-1.0 equipment.** S23 Ultra + MSI G27C4X
   instead of S21 FE + Asus laptop, if the partnership has access.
   This gives us comparable conditions to V2.1's successful run.
2. **Test against B1 benchmark artifacts as well.** Specifically
   `b1-corners-fiducials` to isolate the pose-recovery layer from the
   phoxoidal-substrate-specific failure modes.
3. **Reference V2.1's RS+Chase decoder as a known-working example.**
   Don't re-derive soft-decision RS — port from V2.1 if the
   phoxoidal-discrete codec needs it.
4. **Be honest about scope.** Spike-9B isn't "validating that screen-
   camera-robust carriers are possible" (V2.1 already did that). It's
   "validating that the phoxoidal-discrete variant of a screen-camera-
   robust carrier specifically passes." Smaller claim, more honest.

## Implications beyond spike-9B

**The phoxoidal-carrier proposal needs to land its honest position
relative to V2.1 explicitly.** Three plausible framings:

1. **Phoxoidal as research parallel to V2.1.** Aurexis ships V2.1 as
   production; phoxoidal-carrier explores the catastrophe-germ
   aesthetic as a research lane that might mature into a V3 substrate.
   Doesn't compete; compounds.
2. **Phoxoidal as a substrate that could replace V2.1.** Higher bar —
   would need to match V2.1's 3,568-byte real-capture demonstration.
   Spike-9A's 4-bits-per-germ × 664 grid slots = 332 bytes raw is
   currently 11× lower density than V2.1.
3. **Phoxoidal aesthetic + V2.1 mechanism.** Use catastrophe-germ
   visuals as the cover image but borrow V2.1's discrete-color-module
   + RS+Chase data-bearing layer underneath. Hybrid that retains the
   thesis aesthetic while inheriting V2.1's proven envelope.

The proposal currently doesn't explicitly choose among these three.
That's a partner-decision item worth surfacing.

## Recommended next moves

1. **Read** `Aurexis_Core_M11_Clean.zip` / the V2.1 decoder source to
   understand the working format precisely.
2. **Run** an existing reference_carrier.png through `run_real_capture_pipeline.py`
   on Bug's existing spike-8B captures to see what Aurexis's pipeline says
   about them. Likely won't decode (different format), but might surface
   actionable data about the captures themselves.
3. **Add cross-references** to ADDENDUM_04 and the spike-8B docs pointing
   at the relevant Aurexis V2 docs.
4. **Decide explicitly** which of the three framings (research parallel /
   replacement candidate / aesthetic+mechanism hybrid) the phoxoidal
   carrier is, and update the proposal accordingly.
5. **Then proceed with spike-9B**, but with the equipment + benchmark
   alignment from above.

## What this audit doesn't change

- Spike-9A's central finding (synthetic channel reproduces real failure;
  16-symbol discrete clears it) is still true and useful.
- The catastrophe-germ continuous substrate's failure on screen-camera
  is still real and now triple-confirmed (real captures, prior art,
  synthetic channel).
- The phoxoidal-carrier proposal's substrate-design freedom is still
  genuinely novel.

## Cross-references

- `/tmp/Aurexis/V2_CAPTURE_PROTOCOL.md` — locked V1.0 protocol
- `/tmp/Aurexis/V2_BENCHMARK_SET.md` — locked B1 artifact set
- `/tmp/Aurexis/05_ACTIVE_DEV/run_real_capture_pipeline.py` — existing real-capture runner
- `/tmp/Aurexis/05_ACTIVE_DEV/RESEARCH_deep_cross_domain.md` — 30-technique survey
- `/tmp/Aurexis/07_VISION_SUBSTRATE/phoxelis_sim/phox_format.py` — Phoxelis .phox format (different from phoxoidal-carrier)
- `/tmp/Aurexis/07_VISION_SUBSTRATE/reports/PHOXELIS_VS_PRIOR_ART.md` — Aurexis's competitive scoreboard with V2.1's 3,568-byte real-capture result
- `phoxoidal_carrier_proposal/refs/aurexis/INDEX.md` — pre-existing Aurexis-reference index in our repo
