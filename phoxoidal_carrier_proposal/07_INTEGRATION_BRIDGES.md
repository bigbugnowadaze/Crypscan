# 07 — Integration Bridges

> Proposed bridge milestones for landing the phoxoidal carrier inside Aurexis Core's gate-and-bridge discipline. Conforms to the format in `00_PROJECT_CORE/HIGHER_ORDER_COHERENCE_BRANCH_CAPSTONE_V1.md` and the gate verification format in `00_PROJECT_CORE/CAPTURE_TOLERANCE_BRIDGE_V1_GATE_VERIFICATION.md`. **Bridge counts and assertion totals listed here are proposals, not commitments — they will be set by Vincent during gate authorship.**

---

## 1. Where this work lands

Per the v4 handoff and `Hard Rules` §3 in this package's `README.md`:

- **Not in v1's frozen surface.** Aurexis Core's `00_PROJECT_CORE/`, `01_RELEASES/`, and `BACKUPS/` directories, plus all 33 git tags and 26 backup branches, are immutable. The proposal does not touch them.
- **Not as a v1 modification.** The phoxoidal carrier substrate is a new substrate; it does not retrofit AXP6 nor change V1 substrate modules.
- **In the V2 research lane, or in a new lane Vincent specifies.** `09_OPEN_QUESTIONS.md` §8 asks Vincent which lane is the right home. For purposes of this bridge proposal, the document assumes **a new "V3 phoxoidal carrier" research lane** parallel to V2, sharing the same engineering discipline and capture protocol substrate but running on its own milestone ladder. If Vincent decides instead that the work belongs inside V2 as a charter amendment (à la V2's Decode Engine Track per `V2_CHARTER_AMENDMENTS.md`), this bridge proposal is straightforward to re-home.

The proposed working folder name (subject to Vincent's revision):

```
Aurexis_Core_WORKING_<date>-phoxoidal-carrier/
or
07_VISION_SUBSTRATE/phoxoidal_carrier/   (if added under existing 07_)
```

The proposed git branch name pattern (mirroring V2's pattern):

```
working/phoxoidal-carrier
backup/phoxoidal-carrier-<YYYYMMDD>-<HHMM>
backup-phoxoidal-carrier-<YYYYMMDD>-<HHMM>
```

These follow Aurexis Core's V1/V2 backup and release isolation rule (`V2_CHARTER.md` lines 39–58): no V2 branch / tag / backup gets reused; new lane uses its own namespace; V1 surfaces stay untouched.

## 2. Branch and bridge structure

The proposal organizes the work into **5 branches** (analogous to the 9 branches Aurexis Core's V1 has, but specific to the phoxoidal carrier substrate). Each branch contains a small number of bridges. Each bridge is a self-contained, gate-verifiable unit of work whose pass criterion is binary: PASS or FAIL.

### Branch P1 — Format and scene assembly (encoder side, no decode)

| # | Bridge | Pass criterion |
|---:|---|---|
| 1 | **`PhoxCar Format Lock Bridge V1`** | A `.3dphox` extension (proposed magic `CRYPSOID_3DPHOX_VCAR_PHOXOIDAL_CARRIER`) is specified, locked, and CI-verified to read/write deterministically. Required chunks defined: payload-bearing germ chunks, manifest cluster, Tier C aesthetic field reference. |
| 2 | **`AXP6 Inner Header Preservation Bridge V1`** | The 48-byte inner header (`aurexis_decode.py` lines 535–548 — magic, version, comp, sizes, sha256, filename) is reproduced byte-identical at the format level. Round-trip test: encoder produces inner header → decoder parses → byte-identical to AXP6 path. |
| 3 | **`Symbol Encoder Bridge V1`** | Compressed payload bytes → 5-coefficient germ vectors → scene placement algorithm. Deterministic. Reverses-correctly (encode + symbol-decode round-trips byte-for-byte). |
| 4 | **`Manifest Cluster Layout Bridge V1`** | Manifest cluster geometry (high-redundancy, structurally distinctive) is specified, encoded, and CI-verified to be locatable from a clean rendered scene by the structural detector. |

**Branch P1 capstone (`PHOXOIDAL_CARRIER_FORMAT_BRANCH_CAPSTONE_V1`):** branch is COMPLETE-ENOUGH when all four bridges pass. Conforms to the format of `00_PROJECT_CORE/HIGHER_ORDER_COHERENCE_BRANCH_CAPSTONE_V1.md`.

### Branch P2 — Renderer integration (CRYPSOID composition)

| # | Bridge | Pass criterion |
|---:|---|---|
| 5 | **`Crypsorender PhoxCar Profile Bridge V1`** | CRYPSOID's renderer renders the new format magic with no GPU dependencies (per `README.md` line 88 of CRYPSOID). All three tiers (A, B, C) dispatch correctly. Render is resolution-flexible. |
| 6 | **`Tier C Aesthetic Field Bridge V1`** | Tier C field design specification: what visual classes are allowed, what intensity-distribution constraints apply (band-limit constraints to avoid contaminating payload germ extraction — see `06_DECODER_RESEARCH_PLAN.md` §4.3). Spec includes test fixtures and CI-verified render correctness. |
| 7 | **`Render Determinism Bridge V1`** | Same scene + same camera + same resolution → same PNG output across runs and platforms (within byte-equality after lossless PNG encode). Deterministic by design — the renderer uses no randomness. |

**Branch P2 capstone (`PHOXOIDAL_CARRIER_RENDER_BRANCH_CAPSTONE_V1`):** branch is COMPLETE-ENOUGH when all three bridges pass.

### Branch P3 — Decoder (the largest research risk; per `06_DECODER_RESEARCH_PLAN.md` §7)

| # | Bridge | Pass criterion |
|---:|---|---|
| 8 | **`Scale-Space Detection Bridge V1`** | Scale-space detector identifies candidate singular points in synthetic carriers with > 99% recall at SNR ≥ 30 dB. Documented localization accuracy. |
| 9 | **`Inverted Germ-Fit Bridge V1`** | Given a known-position synthetic germ, recover its 5 coefficients within tight numerical tolerance (e.g., per-coefficient RMSE < 5% of physical range). Verified against CRYPSOID's `tools/crypsorender/math/germ.py` ground-truth forward fit. |
| 10 | **`Mumford-Shah Localization Bridge V1`** | Sub-pixel localization of detected singularities to ≤ 0.5-pixel error on synthetic data. |
| 11 | **`Persistent Homology Confidence Bridge V1`** | Persistent-homology score per detected germ matches the synthetic ground-truth's expected stability ordering. Detected germs ranked by confidence track expected SNR ordering. |
| 12 | **`Manifest Cluster Detection Bridge V1`** | Manifest cluster is detectable from a clean rendered carrier and from a synthetic-warp-degraded carrier (within the §15 Synthetic Tolerance Profile). Decoder bootstraps from the cluster correctly. |
| 13 | **`Synthetic Forward Roundtrip Bridge V1`** | Encoder → renderer → decoder reproduces input payload byte-exact under zero capture noise. SHA-256 verification gate per `aurexis_decode.py` lines 583–585. |

**Branch P3 capstone (`PHOXOIDAL_CARRIER_DECODER_BRANCH_CAPSTONE_V1`):** branch is COMPLETE-ENOUGH when all six bridges pass. **This is the hard branch.** `06_DECODER_RESEARCH_PLAN.md` §4.6 estimates 6-9 months of focused engineering for this branch alone.

### Branch P4 — Tolerance and capture validation (V2 protocol composition)

| # | Bridge | Pass criterion |
|---:|---|---|
| 14 | **`Synthetic Tolerance Profile Bridge V1`** | Decoder works under a synthetic noise tolerance profile in the form of `00_PROJECT_CORE/CAPTURE_TOLERANCE_BRIDGE_V1_GATE_VERIFICATION.md` §"Tolerance Profile Summary". Profile includes scale, translate, blur, noise, brightness, contrast, JPEG quality, and (new for phoxoidal) perspective tilt and lens warp ranges. |
| 15 | **`V2 Capture Protocol Composition Bridge V1`** | Phoxoidal carrier renderable + capturable via V2's existing protocol (`V2_CAPTURE_PROTOCOL.md`, `V2-CAP-PROTO-1.0-LOCK`) without protocol modification. Decoder ingests the captured image. |
| 16 | **`Captured-Image Roundtrip Bridge V1`** | At least one V2-protocol capture decodes byte-exact (SHA-256 match against original payload). The success criterion mirrors `V2-D4` (`V2_ROADMAP.md` line 196: "At least one HD config (128x128-4c) achieves byte-exact decode from real camera capture"). |
| 17 | **`Working-Envelope Characterization Bridge V1`** | Documented decode-success curve as a function of capture parameters (tilt, distance, lighting). Honest failure-mode taxonomy per V2's M4 (`V2_ROADMAP.md` lines 67–73). |

**Branch P4 capstone (`PHOXOIDAL_CARRIER_CAPTURE_BRANCH_CAPSTONE_V1`):** branch is COMPLETE-ENOUGH when all four bridges pass. This is the bridge to "the proposal works in the real world."

### Branch P5 — Integration and release hardening

| # | Bridge | Pass criterion |
|---:|---|---|
| 18 | **`Cross-Branch Compatibility Bridge V1`** | All five branches' artifacts compose end-to-end. CI runs the full encoder → renderer → decoder pipeline on multiple synthetic payloads + at least one captured carrier. |
| 19 | **`Code Provenance Audit Bridge V1`** | Phoxoidal carrier code is clean-room (per Aurexis Core's `CODE_PROVENANCE_AUDIT_V1.md` standard). CRYPSOID code under its license, Aurexis Core code under its license; new code clearly attributed. |
| 20 | **`No-GPU Hard-Rule Bridge V1`** | CI-verified that no `torch`, `cuda-toolkit`, `nvidia-*`, `gsplat`, etc. enters the dependency tree. Mirrors CRYPSOID's existing CI banned-package check (`README.md` line 76). |
| 21 | **`Phoxoidal Carrier Candidate Release Bridge V1`** | Locked release zip + manifest + provenance audit, in the format of `01_RELEASES/aurexis_core_v2_calibration_candidate_locked.zip` (`V2_ROADMAP.md` line 122). Reproducible from working tree. |

**Branch P5 capstone (`PHOXOIDAL_CARRIER_INTEGRATION_BRANCH_CAPSTONE_V1`):** branch is COMPLETE-ENOUGH when all four bridges pass. **This is the bridge to "the substrate is releasable."**

### Branch totals (proposed)

| Branch | Bridges | Indicative target |
|---|---:|---|
| P1 — Format and scene assembly | 4 | Self-contained, ~1-2 months |
| P2 — Renderer integration | 3 | ~1 month given CRYPSOID's existing renderer |
| P3 — Decoder | 6 | **The hard branch — 6-9 months** |
| P4 — Tolerance and capture | 4 | ~2 months after P3 |
| P5 — Integration and release | 4 | ~1 month after P4 |
| **Total** | **21 bridges** | **~12-15 months end-to-end** |

The 21-bridge total is in the same scale as Aurexis Core's V1's 51-bridge total — a substantial-but-bounded body of work. If Bug and Vince accept the proposal, gate authorship sets the actual assertion counts (Aurexis Core V1 averages ~125 assertions per bridge; the phoxoidal lane will likely be similar).

## 3. Cross-branch dependency graph

```
P1 (format + scene assembly)
     │
     ▼
P2 (renderer integration)
     │
     ▼
P3 (decoder)              ← longest poll
     │
     ▼
P4 (tolerance + capture)
     │
     ▼
P5 (integration + release)
```

P1 and P2 can run partially in parallel (P2 needs P1's format spec but not the manifest cluster work). P3's six bridges have their own internal sequencing (detection → localization → fit → confidence → cluster detection → roundtrip). P4 cannot start before P3.13 (synthetic forward roundtrip) passes. P5 cannot start before P4.16 (captured-image roundtrip) passes.

## 4. Mapping to the v4 handoff's "specific landing points in Aurexis Core" §

The handoff's §"Specific landing points in Aurexis Core" listed Aurexis Core branches the proposal intersects. The mapping into the bridge structure above:

| v4 handoff landing | Phoxoidal-carrier composition |
|---|---|
| **Branch 1 (Static Artifact Substrate)** — foundation layer | Branch P1 + P2 inherit this substrate philosophy; phoxoidal carrier is bounded, deterministic, law-governed in the same sense. |
| **Branch 2 (Screen-to-Camera Temporal Transport)** — direct fit | Branch P4 is the analog — captured-image roundtrip via V2-protocol screen-to-camera transport. |
| **Branch 3 (Higher-Order Coherence / Sheaf-Style Composition)** — already in v1 | Composed into Branch P3.11 (sheaf-style consistency for confidence) and Branch P3.13 (decoder uses it for global integrity verification per `03_PHOXOIDAL_CARRIER_ARCHITECTURE.md` §5.3). |
| **Branch 4 (View-Dependent Markers / 3D Moment Invariants)** — already in v1 | Phoxoidal germs ARE 3D moment invariants in CRYPSOID's specific basis. Composed into Branch P1.3 (symbol encoder) and Branch P3.9 (germ-fit). |
| **Branch 5 (VSA / Hyperdimensional Cleanup)** — already in v1 | Optional Phase 2+ extension to Branch P1.3 — replace 8-bit-per-coefficient symbol encoding with VSA hypervector binding (`03_PHOXOIDAL_CARRIER_ARCHITECTURE.md` §6 option 3). Not in the Phase 1 bridge list above; flagged as a future extension. |
| **Branch 7 (Observed Evidence Loop / Real Capture Calibration)** — capture validation lane | Branch P4 explicitly composes with this — V2's capture protocol IS the real-capture calibration substrate. |

The composition is not "land in one branch." It is a five-branch composition where each branch builds on existing Aurexis Core capability and CRYPSOID code where possible, and adds new code only where neither substrate already provides what's needed.

## 5. Gate format reference

Each bridge produces a gate-verification document in the format of `00_PROJECT_CORE/CAPTURE_TOLERANCE_BRIDGE_V1_GATE_VERIFICATION.md`. The skeleton:

```markdown
# <BRIDGE NAME> V1 — GATE VERIFICATION

**Date:** <ISO-8601>
**Milestone:** <Bridge name>
**Scope:** <one-sentence scope of the bridge>

---

## Gate Checks

### 1. <First check>
**STATUS: PASS** | **STATUS: FAIL**
- <bulleted facts establishing the check>

### 2. <Second check>
...

### N. Framing Stays Narrow and Honest
**STATUS: PASS**
- <module docstrings that match the claim, with no overclaiming>

## <Optional sections — Tolerance Profile, Known Limitations, Files>

## Gate Result
**N/N PASS — <Bridge> V1 gate satisfied.**
```

Each branch capstone is in the format of `00_PROJECT_CORE/HIGHER_ORDER_COHERENCE_BRANCH_CAPSTONE_V1.md`:

```markdown
# <BRANCH NAME> Branch — Capstone Verification V1

**Date:** <ISO-8601>
**Status:** BRANCH COMPLETE-ENOUGH
**Verdict:** All <N> <branch theme> milestones verified as a coherent bounded branch.

## Branch Overview
...

## Branch Milestones
| # | Bridge | Milestone | Assertions | Status |
|---|--------|-----------|------------|--------|
| <N1> | <Bridge V1> | <theme> | <count> | ✅ PASS |
...

## Standalone Runner Results
...

## Honest Limitations
...

## What This Branch Proves
...
```

This is the engineering register the proposal would land in. It matches what Vincent's project already does, not a new format.

## 6. What this bridge plan is NOT

- Not a Gantt chart. The estimates are honest engineering estimates, not commitments. Real timelines depend on specific people available at specific times under specific other priorities.
- Not authoritative assertion counts. Aurexis Core's bridge authorship is Vincent's to set; the assertion-count column above is omitted from each bridge entry deliberately.
- Not a release schedule. The "P5 capstone passes" point is the *technical readiness for release*, not a marketing date; release timing is a project-management decision separate from technical readiness.
- Not a substitute for the actual bridge documents. If the proposal is adopted, each of the 21 bridges above gets its own gate-verification document of the format in §5; this `07` doc only proposes their existence and structure.

## 7. Alignment with Aurexis Core's existing posture

Two specific alignments to make explicit so the reviewer sees the bridge plan respects the existing engineering culture:

### 7.1 Frozen-V1 isolation (every gate)

Every bridge gate above includes the gate-rule from `V2_MILESTONE_GATES.md` §"V1 / V2 backup and release isolation":

> No gate on any milestone passes if the V2 tree has reused or mutated any `backup/v1-...` branch, ... force-pushed, deleted, renamed, or retagged any V1 ref.

Adapted to the phoxoidal lane: no phoxoidal-carrier gate passes if it has touched any V1 ref OR any V2 ref outside the new lane's namespace. This is a mechanically-checkable precondition that runs before every gate.

### 7.2 Honesty checks (every gate)

Every bridge gate above includes a "Framing Stays Narrow and Honest" check matching `CAPTURE_TOLERANCE_BRIDGE_V1_GATE_VERIFICATION.md` §"7. Framing Stays Narrow and Honest":

> Module docstring: "Bounded capture tolerance path" / "synthetic non-ideal tolerance proof"
> Does NOT claim: real-world camera robustness, print/scan robustness, general CV resilience, full image-as-program completion

Adapted to the phoxoidal lane: every bridge's module docstring claims only what it actually proves. Bridges that are synthetic-only say so; bridges that work only inside the V2-protocol envelope say so; the working-envelope bridge (P4.17) is the one that earns the broader "captured-image robustness" claim, and only inside its measured envelope.

This is the engineering posture both projects already share, made explicit for the new lane.

---

**Cross-references.** The architecture the bridges land is in `03_PHOXOIDAL_CARRIER_ARCHITECTURE.md`. The decoder branch (P3) is detailed in `06_DECODER_RESEARCH_PLAN.md`. The honest tradeoffs each bridge must respect are in `08_HONEST_TRADEOFFS.md`. The open questions about which lane this work lives in are in `09_OPEN_QUESTIONS.md` §8.
