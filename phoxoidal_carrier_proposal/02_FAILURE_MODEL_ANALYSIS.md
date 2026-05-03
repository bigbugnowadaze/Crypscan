# 02 — Failure Model Analysis

> What AXP6 defends against, what it doesn't, and the structural argument that pixel-grid encodings cannot fully close the V2 gap with more redundancy.

---

## 1. AXP6's failure model — what it actually defends against

AXP6 is a smart, honest engineering response to one specific failure regime: **discrete localized corruption inside a known coordinate system, applied to a clean digital file**. Each of its defenses is well-aimed at a sub-class of that regime.

### 1.1 Localized pixel-level damage → CRC detects, parity recovers

AXP6's neighborhood-linked CRC-8 (`aurexis_decode.py` lines 369–399, see `01_AXP6_ARCHITECTURE_DIGEST.md` §8.2) detects per-block damage and *localizes* it via the link — a single corrupted block surfaces as a CRC mismatch on itself plus the block to its right and the block below. Per-tier XOR parity (lines 617–635) then permits recovery if the damage stays within a parity group's recovery limits (the Python decoder reports failure; the Node decoder reportedly performs recovery — `DECODE_GUIDE.md` lines 110–112).

This is the right defense for: scratches, smudges, ink bleeds, small smears, partial physical occlusion of small regions, and storage-media bit-flips localized to small contiguous runs.

### 1.2 Block-aligned distributed damage → interleaving spreads it

The tier-aware round-robin interleaver (lines 260–267) ensures that physically adjacent damage on the carrier image lands on payload bits that belong to *different* parity groups in the tier stream. So a damage event that takes out (say) a 4×4 block of carrier modules disperses across many parity groups instead of overwhelming one — exactly the right pattern for parity to handle the load.

### 1.3 Edge clipping → EDGE tier carries the most-disposable bits

The positional tier system (lines 222–255, `01_AXP6_ARCHITECTURE_DIGEST.md` §5) places the most-protected bits at the carrier's center (CORE), the next most at one ring in (BODY), and the most-exposed bits on the outer ring (EDGE). EDGE has no parity at all because it is the most likely to be physically clipped or damaged — protecting it would be a wasted budget.

### 1.4 Storage / transit corruption → SHA-256 catches what slipped past the per-block defenses

The 32-byte SHA-256 hash of the original payload (`aurexis_decode.py` lines 543–544 for storage, 583–585 for verification) is the final gate. Anything that survives parity and CRC must still hash-match. This is bit-exact correctness as a hard contract, not a soft one.

### 1.5 What this regime looks like in practice

Picture: Vince emails a `.axp6.png` file to Bug. The file traverses email infrastructure (no transformation — just byte-for-byte transit). Bug saves it to disk. Bug runs `aurexis_decode.py`. The PNG might have a few flipped bits from a borderline-bad disk sector or a glitched USB transfer; AXP6's tiered parity + CRC absorbs that and the file decodes byte-exact.

Or: the PNG gets briefly stored in a service that re-encodes "image attachments" by re-saving them as PNG (a destructive step — see why most carriers fail this in §4 below). AXP6 is a 2-bit indexed PNG; if the re-encoder preserves indexed PNG and the palette, AXP6 survives. If the re-encoder forces RGB or premultiplies an alpha, AXP6 is destroyed. AXP6's defense here is "use byte-preserving channels"; this is a deployment constraint, not a failure-model statement.

These are real workflows. AXP6 ships, it works, the SHA-256 verification at the end of `decode()` is the proof.

## 2. AXP6's failure model does **not** include capture-mediated transformations

`DECODE_GUIDE.md` confirms the deployment shape AXP6 is built for (line 33):

> Vince sends you a PNG file (e.g. `report.json.axp6.png`).

Vince sends you a PNG. Not a photograph of a PNG. Not a screen capture of a PNG. A PNG file, as bytes, on disk, opened by `read_indexed_png()` which expects PNG color type 3 at bit depth 2 (`aurexis_decode.py` line 84). The decoder operates on the **clean digital file**, not on a real-camera image of a displayed or printed carrier.

This is not a hidden assumption — it is the obvious right scope for AXP6 as currently deployed. AXP6 is brilliant at file-to-file workflows. It is not built for capture-mediated workflows, and it does not need to be in order to do its current job correctly.

The V2 frontier (`V2_CHARTER.md` line 13) is exactly the capture-mediated regime:

> V2 takes the V1 substrate ... and puts it through a solo-feasible, screen-based, real-world calibration loop. V2 proves Aurexis Core can ingest controlled real camera evidence, measure its own failure modes against a frozen benchmark, calibrate from the observed evidence, and demonstrate measurable before/after improvement on the same setup.

V2 is *deliberately* opening the door AXP6 was not built to defend.

### 2.1 What happens to AXP6 carriers under capture

If an AXP6 PNG is displayed on a screen and re-photographed by a phone camera (per the `V2_CAPTURE_PROTOCOL.md` setup: Galaxy S23 Ultra, MSI G27C4X, handheld, ~70-90% framing), the phone's image sensor receives a transformed image. The transformations are not random noise; they are *structured*:

- **Perspective tilt.** The phone's optical axis is "as close to perpendicular to the screen center as the operator can maintain" (`V2_CAPTURE_PROTOCOL.md` line 117). It is not exactly perpendicular. Pixels off-center sit at non-trivial homographies away from where the encoder put them.
- **Curved-monitor geometry.** The MSI panel is curved (`V2_CAPTURE_PROTOCOL.md` line 297, listed as a known taxonomy item): "off-axis pixels are physically closer/further than on-axis pixels relative to the phone." The transformation is not even a simple homography.
- **Rolling shutter shear.** Phone CMOS sensors capture rows sequentially, not simultaneously. Hand tremor over the ~10-30 ms readout window introduces row-dependent shear.
- **Focus blur.** Focus is set "tap-to-focus on the artifact's center region" (`V2_CAPTURE_PROTOCOL.md` line 53). Off-center regions and curved regions sit at different focal distances; some part of the carrier is always slightly out of focus.
- **Lens warp.** Even after factory-calibrated correction, residual barrel/pincushion distortion persists. This is not noise; it is a smooth deformation of the coordinate system.
- **Moiré.** Sensor pixel grid against panel sub-pixel grid (`V2_CAPTURE_PROTOCOL.md` line 300, taxonomy item: "Moire / aliasing between panel pixel grid and phone sensor grid"). Periodic structured noise that defeats the parity scheme by adding correlated errors across the carrier.

Every one of these is a **smooth coordinate transformation** of the carrier's image plane, not a discrete localized corruption. None of them lose information; they relocate it.

### 2.2 Why AXP6 cannot find blocks under any of these

`assign_tiers()` cannot run because it cannot find the blocks. The function takes `blocks_w` and `data_blocks_h` as inputs (`aurexis_decode.py` line 222) — those are recovered from the manifest, which itself sits in row 0 between sync columns at known integer pixel coordinates. If those coordinates are not where the encoder put them — and after capture they aren't — there is no manifest, no tier map, no tier extraction, no parity, no CRC, no payload.

The point is structural, not parameter-tuning. AXP6's tier mapping is a *function of integer block coordinates*. There is no other input. If the integer block coordinates are unknown or warped, the tier map is undefined. Parity and CRC can defend against bit-flips inside a known coordinate system; they cannot defend against the coordinate system being warped.

## 3. The structural argument — why pixel-grid encodings cannot fully close this gap with more redundancy

This is the load-bearing claim. It is a structural argument, not an empirical one.

### 3.1 Redundancy is information protection inside a coordinate system

Reed-Solomon codes, parity blocks, CRCs, hashes, repetition codes — every classical channel-coding construction operates the same way: given a fixed code alphabet (bits, modules, bytes) at fixed positions in a code stream, you add extra symbols at other fixed positions whose values are functions of the data symbols. The receiver knows which positions are data and which are check, recomputes the check, and accepts/rejects/corrects as appropriate.

Every step requires the receiver to know **which positions are which**. Coordinate certainty is a precondition. The redundancy budget protects against **value errors** at known positions; it does not protect against **position errors** in the global coordinate system.

### 3.2 Capture warp is a position error in the global coordinate system

A perspective tilt rewrites every input pixel coordinate as a fractional location in the captured image, and then the camera samples those fractional locations onto the integer sensor grid. Lens warp, rolling shutter shear, and curved-monitor geometry compose with the perspective. The composition is a smooth function from "the encoder's grid" to "the sensor's grid." It is bijective (no information lost in the limit of perfect optics) but it is not the identity.

A pixel-grid decoder confronted with a captured image must, before it can use any classical defense, *invert this smooth function* to recover the encoder's grid. That inversion is the missing step.

### 3.3 The two honest options for solving inversion inside a pixel-grid architecture

**Option A — pre-decode geometric correction.** Use fiducial markers (e.g., the four corners of the carrier, or a calibration pattern in the EDGE tier) to estimate the homography or higher-order warp, then resample the captured image back onto the encoder's grid before running the AXP6 decoder. This is real CV engineering: it works for clean lab captures, it gets brittle in low-light or with partial occlusion, and it cannot fully correct rolling shutter (which is non-rigid) or curved-monitor geometry (which is non-projective). The recovered grid will be approximate; small residual sub-pixel error degrades CRC accuracy at the block boundaries because the 2-bit module values are sensitive to which fractional pixel the resampler grabbed. This buys back *some* robustness in the bright-clean-static regime, fundamentally cannot buy back robustness in the moving-blurred-tilted regime.

**Option B — massive over-redundancy at the carrier level.** Add Reed-Solomon redundancy at the module layer, replicate the manifest at known positions across the carrier, etc. This eats payload capacity proportional to the redundancy ratio. More importantly, it does not solve the position-error problem — it solves the value-error-after-grid-recovery problem. RS at the module layer cannot tell you where module 0 starts in a tilted image any more than parity can.

Option A and Option B compose: do both, get more robustness than either alone. But composition still does not dissolve the structural problem. There is a scale of capture-mediated transformation under which (A) cannot recover the grid accurately enough for (B) to work, no matter how much redundancy budget you spend. This is the V2 frontier.

### 3.4 The architecturally honest move

The architecturally honest move — once it becomes clear that the failure regime has shifted from "value errors inside a known grid" to "the grid itself is unknown" — is to stop building defenses inside the pixel-grid assumption and start building on a substrate whose features are *invariant* to the smooth coordinate transformations the new failure regime produces.

That is what `03_PHOXOIDAL_CARRIER_ARCHITECTURE.md` proposes. The substrate change is not motivated by "AXP6 has a bug"; it is motivated by "AXP6's substrate is the wrong unit for the new failure regime, and there is no amount of in-substrate redundancy that will fix that."

## 4. Where this argument can fail (the honest doubts)

`08_HONEST_TRADEOFFS.md` collects every "this is harder than it sounds" point. The argument in §3 above can fail in any of these ways, and the reviewer should weigh them:

1. **The V2 frontier might not actually be capture-mediated for the workflows that matter.** If AXP6's deployment continues to be file-to-file (Vince emails Bug a PNG), the structural argument applies but is irrelevant. Whether this is true is a product/strategy question Bug and Vince must answer (`09_OPEN_QUESTIONS.md` §1).

2. **Pre-decode geometric correction might be enough for the workflows that matter.** Option A in §3.3 is not "useless"; it is "not enough for arbitrary capture." If the capture regime is restricted enough (lab-grade lighting, fixed mount, fixed distance, no motion), Option A may close the gap practically. The V2 protocol (`V2_CAPTURE_PROTOCOL.md`) is in fact deliberately constrained in exactly this direction — it is the "bright-clean-static" baseline where Option A might suffice. The proposal's diffeomorphism-invariance argument matters most in the regime *outside* the V2 protocol's constraints (handheld in low light, mid-motion, off-axis). Whether that regime is on the project's roadmap is `09_OPEN_QUESTIONS.md` §2.

3. **Diffeomorphism invariance is a theorem, but the engineering distance from theorem to working decoder is real.** `06_DECODER_RESEARCH_PLAN.md` is the doc that takes the engineering distance seriously. It is the riskiest single technical chunk of this proposal.

4. **The phoxoidal carrier might not actually achieve the diffeomorphism invariance the architecture claims for it, in practice.** A real germ-extraction pipeline must handle imperfect optics, photon noise, finite sample resolution, and adversarial natural backgrounds. The math gives invariance under *smooth* transformations; real captures include sharp transformations (e.g., partial occlusion) where the smoothness assumption breaks down. `04_DIFFEOMORPHISM_INVARIANCE_ARGUMENT.md` §4 names these honestly.

5. **Information density might not be acceptable.** `05_INFORMATION_DENSITY_ANALYSIS.md` does the back-of-envelope. The numbers are within an order of magnitude of AXP6, not exact parity. Whether the trade is acceptable is `09_OPEN_QUESTIONS.md` §6.

These are real doubts. The proposal does not pretend they are not real. It claims that *under a workflow assumption that includes capture-mediated transports*, the architectural move clears more frontier than it costs — but that assumption is the load-bearing one and Bug and Vince should agree on it explicitly before adopting.

## 5. Sub-claim: AXP6 does not have to be deleted

This deserves its own subsection because it could otherwise sound like a recommendation to throw away working code.

AXP6 is correct, well-built, and the right tool for **digital file → digital file workflows**. It should keep shipping for those workflows. The proposed phoxoidal carrier is the right tool for **capture-mediated workflows**. They serve different deployment regimes; they can coexist as parallel substrates with a clear deployment-time choice. (`Hard rules` §4 in the README, taken from the v4 handoff.)

The naming question (`09_OPEN_QUESTIONS.md` §3) and the deprecation question (`09_OPEN_QUESTIONS.md` §4) are genuinely open. The architecture in `03_PHOXOIDAL_CARRIER_ARCHITECTURE.md` does not assume AXP6 is going away.

## 6. Summary table — AXP6 vs the V2 frontier

| Failure type | AXP6 defense | Holds? |
|---|---|---|
| Single-bit flip in transit | SHA-256 catches; parity often recovers | ✅ Yes |
| Localized scratch / smudge / ink bleed (if printed) on a clean grid | CRC detects, parity recovers within group | ✅ Yes for moderate damage |
| Edge clipping during printing/storage | EDGE tier carries the most-disposable bits | ✅ Yes (graceful degradation) |
| Block-aligned damage that respects the grid | Round-robin interleaving distributes across parity groups | ✅ Yes |
| Re-saving as a different PNG profile (RGB, premultiplied alpha) | None — this destroys 2-bit indexed structure | ❌ No (deployment constraint) |
| Perspective tilt during real-camera capture | None — cannot find blocks | ❌ No |
| Rolling shutter shear during real-camera capture | None — non-rigid; resampling cannot fully invert | ❌ No |
| Focus blur over part of the carrier | None — sub-pixel sampling errors flip module values | ❌ No |
| Lens warp / barrel-pincushion residuals | None — even after correction, sub-pixel residual errors | ❌ Mostly no |
| Moiré between panel and sensor grids | None — adds correlated noise across the carrier | ❌ No |
| Curved-monitor non-projective geometry | None — fiducial homography can't model non-projective | ❌ No |

The bottom block is the V2 frontier. This is the gap the phoxoidal carrier is designed to close.

---

**Cross-references.** The architecture that closes the gap is in `03_PHOXOIDAL_CARRIER_ARCHITECTURE.md`. The math claim that the gap is closeable is in `04_DIFFEOMORPHISM_INVARIANCE_ARGUMENT.md`. The honest accounting of how hard closing it actually is, is in `08_HONEST_TRADEOFFS.md`.
