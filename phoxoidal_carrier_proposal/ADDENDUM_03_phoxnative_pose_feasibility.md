# Addendum 03 — Phoxoidal-Native Pose Feasibility (post-P3.B)

**Status:** Phase 1 follow-up to PR #11 (Phase 1 P3.A) and ADDENDUM_02 (hybrid identity)
**Authored:** 2026-05-04
**Updates:** `ADDENDUM_02_hybrid_identity.md` partner-decision item 4.1 with P3.B's empirical
finding that phoxoidal-native pose recovery is **feasible**, not aspirational.

This addendum is informational and answers a specific question raised by
ADDENDUM_02: does the catastrophe-germ thesis HAVE to defer to conventional
CV (ArUco/AprilTag) for the pose layer, or can it carry that layer too?

**Empirical answer: it can carry the layer.** P3.B opens a third partner-decision
path beyond the binary "ship hybrid" vs "wait for phoxoidal-native".

---

## 1. The empirical finding from P3.B

P3.B (`phoxcar/p3b_phoxnative/`) replaces P3.A's ArUco markers with
**phoxoidal-native corner clusters** detected by **normalized
cross-correlation (NCC) matched-filter** against the same germ templates
the encoder used. The detector kernel IS the catastrophe-germ basis.

Result against the same ChatGPT acceptance gate as P3.A:

| Envelope axis | P3.A (ArUco) | P3.B (phoxoidal-native, v0) |
|---|---|---|
| Photometric (gamma 0.7-1.4, brightness ±0.10, contrast 0.6-1.4, JPEG ≥15, gaussian ≤0.10, blur ≤1.5, salt-and-pepper ≤0.05) | Full pass | **Full pass** (matches P3.A) |
| In-frame translation (≤60 px) | Pass | Pass |
| Sub-pixel offset | Pass | Pass |
| In-frame scale (0.7-1.0) | Pass | Pass |
| Shear ≤5° | Pass | Pass |
| Tilt ≤10° | Pass | Pass |
| Rotation 0/90/180/270° | Pass (ArUco rotation-invariant) | Fail at >5° (saddle/trefoil rotational symmetry — fixable) |
| Rolling shutter ≤1.0 px/row | Pass (ArUco quad-detection tolerates row shear) | Fail at any non-zero severity (NCC rigid-template — fixable) |
| Off-canvas warps | Fail (synthetic-test artifact) | Fail (same artifact) |

**The headline:** the photometric envelope is fully met using ZERO
conventional CV. The geometric envelope is narrower at extreme orientations
but matches P3.A in-frame.

## 2. Implications for ADDENDUM_02 §4.1

ADDENDUM_02 §4.1 framed the partner decision as binary:
- **Accept the hybrid** (P3.A as production, ArUco corners visible)
- **Reject the hybrid** (block production until P3.C phoxoidal-native is
  envelope-equivalent — adds 4-6 weeks per the addendum estimate)

P3.B opens a **third path**:

- **Ship hybrid AND develop phoxoidal-native in parallel.** The production
  substrate stays P3.A (ArUco) for V1; P3.C iterations close the
  P3.B-vs-P3.A geometric gap in the background; the production substrate
  migrates to phoxoidal-native when envelope parity is reached.

This decouples the V1 ship date from the thesis-purity question. V1 ships
on P3.A's tested envelope; thesis-purity ships when P3.C reaches envelope
parity (estimated 2-4 spike iterations beyond P3.B v0).

## 3. P3.C iteration roadmap

Each iteration is a focused multi-day spike that opens one envelope axis:

### 3.1 P3.C v1: asymmetric corner glyphs (rotation envelope)

Replace the saddle/trefoil corner glyphs (rotational symmetries) with
fully-asymmetric germs designed to be self-distinct under all 90/180/270°
rotations. Probably opens rotation envelope to full 360° (matches ArUco).

Design criterion: 4 germs whose pairwise NCC at all 4 cardinal rotations
is < some threshold. Computable by greedy search in c_ortho space against
the same farthest-point sampling discipline as the codebook.

Estimated effort: 1-2 weeks.

### 3.2 P3.C v2: affine-deformable template matching (rolling shutter)

Replace rigid NCC with an ArUco-style quad detector adapted to germ
clusters. Detects the cluster outer boundary as a quadrilateral
(possibly perspective-tilted or row-sheared), then samples interior
germs for identification. Opens rolling shutter envelope.

Estimated effort: 2-3 weeks.

### 3.3 P3.C v3: multi-rotation NCC (small-angle robustness)

Search NCC at multiple rotations (e.g. {-30°, -15°, 0°, +15°, +30°})
in addition to multiple scales. Opens moderate-rotation envelope to
~±30° even with the symmetry-broken P3.C v1 glyphs.

Estimated effort: 1 week (mostly compute; ~5x slower detection).

After v1 + v2 (and optionally v3), phoxoidal-native pose recovery would
be positioned to match P3.A's full envelope. At that point the substrate
becomes **fully thesis-aligned end-to-end** and the ArUco hybrid can be
retired.

## 4. New `09_OPEN_QUESTIONS.md` items raised by P3.B

These supplement the joint partner-decision items in ADDENDUM_02:

### 4.4 Production deployment strategy

Three options now exist:

| Option | V1 ship date | Thesis purity | Engineering risk |
|---|---|---|---|
| Ship P3.A as production, no further pose work | Today | Mixed (ArUco visible) | Low |
| Block V1 until P3.C reaches envelope parity | +4-6 weeks (estimate) | Pure | Medium |
| Ship P3.A as production, develop P3.C in parallel | Today | Mixed for V1, pure for V2 migration | Low (concurrent paths) |

**Joint decision question:** which path does the partnership pick?

### 4.5 P3.C v1 design criterion

The phoxoidal corner-glyph design needs a clear pairwise-NCC criterion
under all relevant transformations (4 cardinal rotations as the minimum
viable, optionally arbitrary rotations). This is a CRYPSOID-thesis-aligned
optimization problem (find 4 germs in c_ortho space that maximize a
multi-rotation pairwise distance metric).

**Joint decision question:** does the partnership want to commission this
design study (requires building a pairwise-NCC distance evaluator,
running greedy search, validating against the P3.B detector)?

### 4.6 V2 substrate identity disclosure

If the partnership picks "ship P3.A, migrate to P3.C later", the V2 carrier
will look DIFFERENT from V1 carriers (corner clusters of phoxoidal germs
instead of ArUco markers). Existing V1 decoders won't decode V2 carriers
and vice versa.

**Joint decision question:** is a V1→V2 substrate migration acceptable, or
should the production format be frozen at V1's ArUco corners to avoid
client-side decoder fragmentation?

## 5. Cross-references

- `phoxcar/p3b_phoxnative/results/P3B_REPORT.md` — full P3.B sweep + analysis.
- `phoxoidal_carrier_proposal/ADDENDUM_02_hybrid_identity.md` — the hybrid-identity
  acknowledgment that P3.B answers.
- `phoxcar/PHOXCAR_CAPTURE_SUBSTRATE_V0.md` — substrate freeze; layer 5 now has
  TWO empirically-validated paths (P3.A ArUco, P3.B phoxoidal-native v0).
- `phoxcar/p3a_aruco/` — the production hybrid pose substrate.
