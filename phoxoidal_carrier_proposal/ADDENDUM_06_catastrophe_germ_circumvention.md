# Addendum 06 — Catastrophe-Germ Circumvention of V2.1 Failure Modes

**Status:** strategic re-read of Aurexis through the right lens
**Authored:** 2026-05-04
**Context:** ADDENDUM_05 surveyed Aurexis as if alignment was the goal.
That misread the intent. CRYPSOID exists *because* Aurexis V2.1's
discrete-module foundation has documented limits the catastrophe-germ
math could **circumvent** — not match, leapfrog. This addendum re-reads
the Aurexis docs with that lens and identifies the radical-but-logical
move that's catastrophe-germ-aligned, not V2.1-aligned.

## Headline

Aurexis V2.1 succeeds (3,568 bytes byte-exact, S23 → MSI, 2026-04-17)
**by patching a fundamentally rigid foundation**. Each of the 30
techniques in `RESEARCH_deep_cross_domain.md` is a *correction* applied
on top of:

- Hard-decision color classification (4 colors per module)
- Discrete RGB module sampling
- Global Otsu thresholding for finder detection
- 4-point homography from finder centers only
- Hard-decision RS over byte-stream

**That foundation has problems catastrophe-germ math doesn't have to
begin with.** Most of Vince's recommended fixes (Chase-2, CIELab,
Sauvola, QPP, Forstner subpixel, sheaf diffusion) are answers to
*questions the catastrophe-germ substrate doesn't ask*. The radical
move is not "16-symbol discrete catastrophe-germs" (spike-9A's path —
which is just adopting Vince's foundation while keeping the visual
aesthetic). It's: **catastrophe-germ math at the channel-matched
scale, with projection-native soft decoding, with multi-frame
catastrophe persistence**.

## Vince's documented failure modes vs catastrophe-germ alternatives

Each of these is something V2.1 hits and is currently patching:

### 1. Hard warp → 13/16 RS block failures

**V2.1 origin:** spatially correlated classification errors concentrate
in localized regions of the module grid. RS blocks have hard per-block
limits; a 10×10 damaged region overwhelms 1-2 blocks completely.

**V2.1 patch:** QPP pseudo-random spatial interleaver (#1 in the
research doc).

**Catastrophe-germ alternative:** germs are **already spatially local**
(Gaussian-weighted basis functions; influence drops off in a few σ).
A damaged region only affects germs whose centers fall within it.
Adjacent germs are *uncorrelated* by construction. **No interleaver
needed; locality is automatic.** The germ basis's L1 separation
property gives this for free.

**Why this is radical:** V2.1 fights spatial correlation with a
permutation table. Catastrophe-germ never has the correlation in the
first place because each datum is already its own local feature.

### 2. Global Otsu thresholding fails under uneven lighting

**V2.1 origin:** thresholds are needed to separate "module" vs
"background" before reading the module's color. Lighting gradients
break global thresholds.

**V2.1 patch:** Sauvola adaptive thresholding via integral images.

**Catastrophe-germ alternative:** **no thresholds.** Decoding is
projection of the captured patch onto the basis. Photometric
calibration uses pilot germs to fit a smooth-varying intensity
transform across the canvas (not a binary threshold). Lighting
gradients are handled by the calibration model, not by chopping at a
brightness boundary.

**Why this is radical:** binary thresholding is a category mistake for
continuous data. Catastrophe-germ never uses one.

### 3. Naive RGB nearest-color classification

**V2.1 origin:** module colors are sampled in RGB (where Euclidean
distance ≠ perceived distance) and classified by nearest-color (which
ignores camera-specific spectral response).

**V2.1 patches:** CIELab classification + Von Kries chromatic
adaptation + reference-patch in-situ calibration (#3, #5, #6).

**Catastrophe-germ alternative:** **bypass color entirely.** Germs are
intensity-only (single-channel grayscale). The substrate doesn't ask
the camera to discriminate between R/G/B at all. The whole color-
calibration stack is irrelevant.

**Why this is radical:** color is V2.1's information-density lever
(4 colors = 2 bits/module). Catastrophe-germ trades that off for
intensity-only, so it has to make up density elsewhere — but it dodges
the entire color-calibration brittleness.

### 4. Hard-decision RS discards confidence information

**V2.1 origin:** classifier outputs a single guess; RS sees binary
right/wrong; no soft information flows through.

**V2.1 patch:** Chase-2 soft-decision (#2): record per-module
confidence margins, generate 2^K candidate codewords, RS-decode each.

**Catastrophe-germ alternative:** **soft information is native.** The
projection magnitude IS the confidence. Each germ's coefficient
estimate has a continuous residual. The decoder can naturally output
per-bit log-likelihoods for ECC consumption. **No Chase machinery
needed; soft is the default.**

**Why this is radical:** Chase-2 is a workaround for substrates that
threw away soft information at the classifier. Catastrophe-germ never
threw it away.

### 5. 4-point homography from finder centers only

**V2.1 origin:** pose recovery uses just the 3 finder centers + 1
alignment center; no information from the rest of the grid.

**V2.1 patches:** LM refinement on all correspondences; Forstner
subpixel (#7, #8, #12); cross-ratio validation (#10).

**Catastrophe-germ alternative:** **every germ contributes to pose.**
A germ's catastrophe-singularity type (fold, cusp, swallowtail) is
projection-invariant. The whole grid can be a pose-refinement
constraint set, not just 4 corners. Better: pose can be recovered
by minimizing global catastrophe-stability across all germs
simultaneously, with no need for separate finder pattern.

**Why this is radical:** V2.1 separates "find the corners" from "read
the data". Catastrophe-germ doesn't have to. Every germ is both data
and constraint.

### 6. Curved-monitor geometry (MSI G27C4X is curved)

**V2.1 origin:** flat-projection homography models assume planar
display. A curved monitor produces non-projective deformation.

**V2.1 patch:** none currently listed in the research doc — this is
on the V2 capture-taxonomy "items to characterize" list, not a solved
problem.

**Catastrophe-germ alternative:** **catastrophe theory was literally
invented to handle curved-surface projections.** The Pearcey-class
basis represents fold/cusp/swallowtail catastrophes — exactly the
singularity types you get when projecting smoothly-curved surfaces.
A curved monitor's projection onto the camera sensor is a fold
catastrophe locally; the basis represents that exactly. **Curvature
becomes signal, not noise.**

**Why this is radical:** Vince has no good answer for the curved-
monitor problem. Catastrophe-germ math has the *right tool from the
start*.

### 7. Single-frame brittleness

**V2.1 origin:** one capture, one decode attempt, no information
fusion across captures.

**V2.1 patch:** registered multi-frame pixel averaging (#13).

**Catastrophe-germ alternative:** **multi-frame catastrophe
persistence.** A germ that decodes to the same coefficient vector
across multiple capture frames is *structurally stable* in the
catastrophe sense. Persistence (in the same sense as topological
persistence diagrams) gives a principled high-confidence selector.
This is multi-frame *reasoning*, not multi-frame averaging — averaging
loses information; persistence preserves it.

**Why this is radical:** V2.1 averages frames pixel-wise. Catastrophe-
germ uses the *theoretical structure* of the basis to identify which
features survived the channel.

## Why spike-9A's "16-symbol discrete" is the wrong move

Spike-9A's recommendation — replace continuous catastrophe-germ codebook
with 16-symbol discrete classifier — **adopts V2.1's foundation while
keeping the visual aesthetic**. It would work, but it discards
catastrophe-germ's actual differentiator: the continuous, structurally-
stable basis representation. We'd be keeping the look while throwing
away the substrate.

**The right move is the opposite:** keep the continuous catastrophe-germ
basis, but redesign the encoding to survive the channel using the basis
itself, not by patching it with discrete classification.

## The radical-but-logical spike: spike-9B-prime

Replace spike-9A's "16-symbol nibble codec" with a **catastrophe-germ-
native channel-matched substrate**:

### Design pillars

1. **Channel-matched germ scale.** Current σ=4 / half_size=12 → germs at
   ~25-pixel scale. Screen-camera channel kills frequencies ≥ 1/5
   cycles/pixel (the moiré band). Bump to σ=8 / half_size=24 → germs at
   ~50-pixel scale, bandwidth concentrated below 1/8 cycles/pixel.
   Density drops 4× but each germ becomes channel-natural.

2. **Projection-native soft decode.** Don't fit 5 coefficients then
   classify. Project the captured patch onto an oversized dictionary
   of germ templates, output the projection-magnitude vector as soft
   information for ECC. The catastrophe-germ basis is naturally
   orthogonal under Gaussian-weighted inner product, so projection is
   well-defined and unbiased.

3. **Spatially-distributed multi-pilot calibration.** Instead of 4
   pilots fitting a global `a + b·I^γ`, distribute 16-32 pilots and
   fit a smooth spatially-varying transform (low-order 2D polynomial,
   thin-plate spline, or local affine patches). Handles curved-monitor
   geometry, lens distortion, vignetting, and lighting gradients in
   one pass.

4. **Pose recovery via grid catastrophe-stability** (stretch goal).
   Instead of separate ArUco corners, recover pose by jointly
   optimizing homography + photometric transform such that all germs
   project to valid catastrophe types. The grid IS the fiducial.

5. **Frame-coherence ECC** (stretch goal). When multi-frame is
   available, use catastrophe-persistence across frames as additional
   ECC information. A germ persistent across 3+ frames is high-
   confidence regardless of single-frame projection magnitude.

### What this would prove

If spike-9B-prime decodes a real S23-or-S21 capture of an MSI-or-Asus
display **using nothing but catastrophe-germ math (no Chase, no QPP,
no CIELab, no Sauvola, no learned CDTF)**, that's the existence proof
the phoxoidal-carrier proposal needs.

It demonstrates a *substrate that handles screen-camera capture
analytically*, where StegaStamp uses learned U-Nets and V2.1 uses
30-technique patching. That's the radical-but-logical position.

### What this avoids

- Adopting V2.1's 30 patches one by one
- Conceding that screen-camera robustness requires neural codecs
- Diluting the catastrophe-germ thesis into "catastrophe-germ aesthetics
  on top of discrete colored modules"

### Estimated effort

3-5 days for the channel-matched scale + projection-native soft decode
(pillars 1-3). 1-2 weeks if pillars 4-5 are folded in. Significantly
more than spike-9A's nibble-codec proposal, but the result is
*architecturally interesting* in a way the nibble codec isn't.

## Honest caveats

- **Density vs robustness trade.** σ=8 germs at 50 pixels mean ~330
  germs per canvas vs the current ~676. With 5 bits/germ continuous
  encoding, that's ~200 bytes/canvas raw. Below V2.1's 3,568 bytes.
  We win on architectural elegance, not density-per-canvas. Density-
  per-area can match later via scale optimization.
- **The pillars 4-5 stretch goals are theoretically sound but
  unbuilt.** The grid-as-fiducial idea and persistence-ECC are
  speculative until proven on synthetic + real data.
- **Catastrophe-germ math is *not magic*.** It's well-suited to
  smooth-singularity recovery from projected images; that's a real
  but bounded advantage. Whether it actually beats StegaStamp's
  empirical numbers is an open question that requires building it.

## Recommended next move

**Authorize spike-9B-prime: catastrophe-germ-native channel-matched
substrate.** Specifically:

1. Implement σ=8 / half_size=24 germs in a new spike directory
2. Test on the existing spike-9A synthetic channel (we already know
   the channel calibrates to spike-8B failure)
3. Implement projection-native soft decode (use full 256-codeword
   codebook but with image-space projection-magnitude vector as
   output, not single nearest-codeword)
4. Implement spatially-distributed multi-pilot calibration (16
   pilots distributed across the canvas, fit a local-affine
   per-quadrant transform)
5. Compare: V0 (P3.A as-is), V1 (V0 + σ=8), V2 (V1 + projection-soft),
   V3 (V2 + multi-pilot)
6. Whichever variant clears synthetic, take to real capture (with
   Bug's S21 FE on whatever screen — equipment-locked V2-CAP-PROTO is
   useful but not required for proof of concept)

The goal is **architectural existence proof**, not density parity with
V2.1. If we have a substrate that decodes screen-camera captures
analytically using only catastrophe-germ projections, the phoxoidal
proposal has empirical legs to stand on.

If spike-9B-prime fails synthetic, we learn that the catastrophe-germ
basis genuinely doesn't survive screen-camera at any scale — and
*that* is when the discrete-classifier or neural-codec fallbacks become
forced.

## Cross-references

- ADDENDUM_04 §3 #2 (bandpass decoder hint — partially overlaps with
  channel-matched scale idea)
- ADDENDUM_04 §4 (LSQ-as-wrong-decoder critique — projection-native
  soft is the principled fix)
- ADDENDUM_05 (prior-work survey — explains what NOT to duplicate)
- `/tmp/Aurexis/05_ACTIVE_DEV/RESEARCH_deep_cross_domain.md` §2-3 for
  Vince's documented limits and patches
- `phoxoidal_carrier_proposal/refs/aurexis/INDEX.md` for Aurexis-side
  citation paths
