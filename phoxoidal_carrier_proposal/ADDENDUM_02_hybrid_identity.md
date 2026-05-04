# Addendum 02 — Hybrid Identity (post-P3.A)

**Status:** Phase 1 follow-up to PR #11 (Phase 1 P3.A: ArUco fiducial pose recovery)
**Authored:** 2026-05-04
**Updates:** `03_PHOXOIDAL_CARRIER_ARCHITECTURE.md` and `09_OPEN_QUESTIONS.md` to reflect the empirical finding that the production substrate is **hybrid**: phoxoidal-native payload + conventional fiducials for pose.

This addendum is informational. The architectural claim of the proposal is unchanged. The empirical engineering path has clarified that production substrate uses two layers with different intellectual provenance.

---

## 1. The empirical finding from spike-8A → P3.A

Spike-8A attempted phoxoidal-native corner finders (high-amplitude codebook glyphs at canvas corners, with topology and template-match identification). Result: zero-warp gate passed; geometric and photometric envelopes were narrow.

P3.A replaced phoxoidal-native finders with OpenCV ArUco DICT_4X4_50 markers. Result: full ChatGPT acceptance gate met for photometric tolerance, in-frame geometric warps all pass.

**The conclusion is empirical, not philosophical.** Mature CV fiducials (AprilTag, ArUco) are the right pose-recovery substrate for the V3 frontier. Phoxoidal-native fiducials are a research aspiration, not a Phase 1 deliverable.

## 2. The production substrate is hybrid

Updates to `03_PHOXOIDAL_CARRIER_ARCHITECTURE.md` §10 layer table (informational; the doc itself is preserved as Phase 0 authoring):

| Layer | Original framing | Post-P3.A framing |
|---|---|---|
| Symbol channel (3) | catastrophe-germ codebook | **CRYPSOID-thesis-aligned (unchanged)** |
| Calibration (4) | catastrophe-germ pilot anchors | **CRYPSOID-thesis-aligned (unchanged)** |
| Pose recovery (5) | manifest cluster + structural detection | **conventional fiducials (ArUco/AprilTag) — pragmatic CV, not catastrophe-germ-native** |
| Carrier display (6) | sigmoid phoxoidal field | **CRYPSOID-thesis-aligned (unchanged)** |

The catastrophe-germ thesis is preserved at every layer where it adds value. **Pose recovery is not where the thesis adds value.** Pose recovery is a known-solved CV problem; ArUco/AprilTag are the known solutions; using them frees engineering capacity to invest where the thesis matters (the symbol channel and the calibration channel).

ChatGPT's audit had this exactly right: "Pose recovery is not the invention. The carrier symbol substrate is the invention."

## 3. Implications for `09_OPEN_QUESTIONS.md`

The "subliminal carrier vs visible alphabet" question (§3 of the original `03` doc) gains a new dimension:

- **Subliminal mode** (carrier looks like a photograph, brand asset, or ambient texture) — phoxoidal germs hide in luminance gradients of a Tier C aesthetic field.
- **Visible-alphabet mode** (carrier looks like a "scannable code") — explicit phoxoidal glyph field, possibly with conventional fiducials for pose.

**P3.A confirms the visible-alphabet mode is engineering-tractable today.** The subliminal mode remains aspirational and would require either:
- A phoxoidal-native fiducial that survives perspective + photometric drift (research path), OR
- Subliminal-compatible markers (e.g., spread-spectrum watermarking-style fiducial bits embedded in the Tier C field's natural structure).

The proposal does not foreclose either. P3.A picks the visible-alphabet path because it is V3-frontier-ready today; subliminal mode can follow later as Phase 1 P3.B research.

## 4. New `09_OPEN_QUESTIONS.md` items raised by P3.A

These are addenda to the joint partner-decision items:

### 4.1 Visible-fiducial aesthetic acceptance

ArUco/AprilTag markers are visually distinct from phoxoidal germs (black/white squares vs smooth phox blobs). Carriers shipped under P3.A look like "phoxoidal interior with conventional QR-style corners."

**Joint decision question:** is this aesthetic acceptable for production deployment? It looks like a hybrid carrier (which it is), and that hybridness is visible.

If unacceptable: Phase 1 P3.B (phoxoidal-native fiducials) becomes a blocker for production, not an aspiration. Adds 4-6 weeks to the production timeline.

If acceptable: P3.A is the production pose substrate; subliminal mode and phoxoidal-native fiducials are post-V1 research.

### 4.2 ArUco dictionary choice

P3.A uses `DICT_4X4_50` (50 unique markers, 4×4 bit data). Alternative dictionaries:
- `DICT_5X5_50`: more bits per marker → more robust ID assignment but larger marker footprint.
- `DICT_4X4_100` / `DICT_4X4_250` / `DICT_4X4_1000`: more unique IDs available.
- `DICT_APRILTAG_36h11`: AprilTag-family, generally more robust to perspective.

Phase 1 might want to upgrade to a larger / more robust dictionary. Empirically `DICT_4X4_50` works at the V3 envelope; the question is whether marginal robustness gains from `APRILTAG_36h11` justify a switch.

### 4.3 Off-canvas warp handling (real-capture artifact)

P3.A's geometric failures all come from synthetic warps pushing markers off-canvas. Real captures have framing slack; the carrier sits with margin around it in the camera frame. This is a synthetic-test artifact, not a production concern.

**However** — extreme captures (operator very close to screen, or pulled back so the carrier is small relative to frame) produce edge cases. Phase 1 P3 should explicitly characterize at what carrier-fill-fraction the substrate fails, and document a recommended capture envelope.

## 5. What stays unchanged

- The catastrophe-germ thesis is preserved.
- The freeze of substrate layers 1-4 + 6-8 (per `phoxcar/PHOXCAR_CAPTURE_SUBSTRATE_V0.md`) is preserved.
- The PHOX-ANALOG / PHOX-CODEBOOK substrate fork in spike-6's report is preserved.
- The 12 deliverables of Phase 0 are preserved as authored; this addendum extends them rather than rewrites them.

## 6. Cross-references

- `phoxcar/PHOXCAR_CAPTURE_SUBSTRATE_V0.md` — the substrate freeze. Layer 5 transitions from OPEN PoC to P3.A SHIPS.
- `phoxcar/p3a_aruco/results/P3A_REPORT.md` — full P3.A acceptance gate measurements.
- `phoxcar/spike8a/results/SPIKE8A_REPORT.md` — proof of concept for sidecar-free decode (architectural validation; superseded as production by P3.A).
- `phoxoidal_carrier_proposal/03_PHOXOIDAL_CARRIER_ARCHITECTURE.md` — original architectural proposal. Layer 5 framing preserved as authored; this addendum supplements with the empirical hybrid finding.
- `phoxoidal_carrier_proposal/09_OPEN_QUESTIONS.md` — joint partner decisions. New items 4.1–4.3 above.
