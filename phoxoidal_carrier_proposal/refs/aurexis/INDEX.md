# refs/aurexis/

Aurexis Core public repo: `https://github.com/KungFury87/Aurexis`

The Phase 0 package cites the following Aurexis Core files. Clone the repo and read at the cited paths to verify.

| Path in Aurexis repo | What the proposal cites it for |
|---|---|
| `README.md` | Project framing ("phoxel field" line 22); engine vs E/D split; ACOR-1.1 release stamp; the 9 Branch Families (lines 252–264) |
| `CORE_TREE_MAP.md` | Repo layout; what is FROZEN vs ACTIVE vs NEW |
| `CORE_UNIFICATION_REPORT.md` | History of the unified working tree |
| `ROADMAP.md` | Unified roadmap |
| `PROJECT_STATUS.md` | Master status tracker |
| `V2_CHARTER.md` | V2 purpose (line 13: real-world calibration loop); V1/V2 backup-and-release isolation rule (lines 39–58); execution constraints (line 84) |
| `V2_ROADMAP.md` | V2-M0..V2-M8 milestones; V2-D0..V2-D4 decode engine track (Amendment 1) |
| `V2_CAPTURE_PROTOCOL.md` | The locked capture protocol `V2-CAP-PROTO-1.0-LOCK`; phone (Galaxy S23 Ultra) + monitor (MSI G27C4X) + handheld + indoor session window; known taxonomy items including curved-monitor geometry, moiré, AWB drift, etc. |
| `V2_PILOT_RUNBOOK.md` | First pilot P1: 5 sessions × 3 captures, B1 artifact ordering |
| `V2_MILESTONE_GATES.md` | Gate format for V2; explicit pass/fail criteria; the V1/V2 isolation rule restated as a gate-level check |
| `V2_BENCHMARK_SET.md` | B1 base static screen family — 5 mandatory artifacts, generators, measurement targets |
| `V2_CHARTER_AMENDMENTS.md` | Decode Engine Track amendment as the model for "lane addition without charter rewrite" |
| `00_PROJECT_CORE/HIGHER_ORDER_COHERENCE_BRANCH_CAPSTONE_V1.md` | Branch capstone format used by `07_INTEGRATION_BRIDGES.md`; the 4 sheaf-style bridges (Overlap Detection, Local Section Consistency, Sheaf-Style Composition, Cohomological Obstruction Detection); 258 assertions; honest-limits framing |
| `00_PROJECT_CORE/CAPTURE_TOLERANCE_BRIDGE_V1_GATE_VERIFICATION.md` | Bridge-gate-verification format used by `07_INTEGRATION_BRIDGES.md`; `V1_TOLERANCE_PROFILE` data shape (scale 0.90–1.10, blur radius ≤ 2, etc.); §"Framing Stays Narrow and Honest" honesty check |
| `00_PROJECT_CORE/CODE_PROVENANCE_AUDIT_V1.md` | Clean-room provenance audit standard the proposal commits to inheriting |
| `06_PROOF_SYSTEM/aurexis_research_sim/README.md` | v0.6 Engine-semantics proof system; seven proof categories; per-family confidence states (TRUST/HOLD/DOWNGRADE/REJECT/NEED_MORE_EVIDENCE) — analogous to the persistence-confidence weighting in the proposed phoxoidal decoder |

## Cited branches in particular

The 9 Branch Families (per `README.md` lines 252–264) the proposal composes with:

- **Branch 1** — Static Artifact Substrate (foundation philosophy)
- **Branch 2** — Screen-to-Camera Temporal Transport (the V2 frontier)
- **Branch 3** — Higher-Order Coherence / Sheaf-Style Composition (sheaf integrity check, used in `03_PHOXOIDAL_CARRIER_ARCHITECTURE.md` §5.3)
- **Branch 4** — View-Dependent Markers / 3D Moment Invariants (germs *are* 3D moment invariants in CRYPSOID's basis)
- **Branch 5** — VSA / Hyperdimensional Cleanup (HDC over germs as a Phase 2+ symbol-encoding option)
- **Branch 7** — Observed Evidence Loop / Real Capture Calibration (V2-protocol composition)

Branches 6, 8, 9 are not directly composed with by this proposal but are consistent with the phoxoidal lane's posture (release hardening, real-capture user handoff, dry-run readiness).
