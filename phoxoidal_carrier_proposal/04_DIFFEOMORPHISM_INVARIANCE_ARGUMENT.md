# 04 — Diffeomorphism Invariance Argument

> The mathematical case for why catastrophe-germ classification survives the smooth coordinate transformations a real camera capture introduces. State precisely what the math gives. Acknowledge precisely what it does not give. The claim must hold up to a mathematician reading it; the limits must hold up to a working engineer reading it.

---

## 1. The claim

**The set of catastrophe germs that classify a smooth map's singularities is invariant under right-equivalence by smooth diffeomorphisms of the source coordinate system.**

In the engineering context of this proposal: if the encoder places germs at positions in a 3D scene and renders the scene to a 2D image, and if a camera captures that 2D image through optics whose total effect (perspective, rolling shutter, focus blur kernel, lens warp, curved-monitor geometry, etc.) is well-approximated by a smooth diffeomorphism of the image plane, then the captured-image germs that the decoder extracts classify into the same catastrophe types as the encoder's germs. The decoder reads the same symbol stream, modulo the diffeomorphism's effect on geometric position (which is a separate concern, addressed in §5).

This is a structural claim. The next subsections give it precisely.

## 2. Precise mathematical statement

### 2.1 Setup

Let `X` and `Y` be smooth manifolds and `f : X → Y` a smooth map. The **singular set** of `f` is the locus where `df` (the differential) drops rank. At each singular point `p ∈ X`, the **germ** of `f` at `p` is the equivalence class of `f` under the relation "agree on a neighborhood of `p`."

Two germs `f` at `p` and `g` at `q` are **right-equivalent** (notated `f ∼_R g`) if there exist:
- A smooth diffeomorphism `φ : (X, p) → (X, q)` of source neighborhoods,
- A smooth diffeomorphism `ψ : (Y, f(p)) → (Y, g(q))` of target neighborhoods,
such that `g = ψ ∘ f ∘ φ⁻¹` as germs.

(Right-equivalence with the source diffeomorphism only — i.e. `g = f ∘ φ⁻¹` — is sometimes singled out and called "right-equivalence" in the strict sense; the definition above is sometimes called "right-left-equivalence" or "𝒜-equivalence." The argument in this document goes through under either convention because the relevant invariants are robust.)

### 2.2 Thom's classification theorem

For smooth maps `f : ℝⁿ → ℝᵏ` with `n ≤ k + 4` and `k ≤ 2`, Thom showed (and Mather and Arnold extended) that the *generic* germ types — i.e. the ones that occur stably under small perturbations — form a finite list, the **elementary catastrophes**. For `n = 2, k = 1` (the case relevant to a 2D image's intensity field), the list is:

| Codimension | Germ type | Normal form | Coefficient role in CRYPSOID basis |
|---:|---|---|---|
| 0 | Morse (regular point) | `s² + t²` (or `s² - t²`) | κ₁, κ₂ (Hessian eigenvalues) |
| 1 | Fold (A₂) | `s³ + t²` | χ controls cubic part |
| 2 | Cusp (A₃) | `s⁴ + t²` (or `±s⁴ + t²`) | ζ controls quartic part |
| 3 | Swallowtail (A₄) | `s⁵ + t²` | (higher-order; not in 5-coef basis) |
| 3 | Hyperbolic umbilic (D₄⁺) | `s³ + st²` | χ, ω |
| 3 | Elliptic umbilic (D₄⁻) | `s³ - st²` | χ, ω |
| 4 | Butterfly (A₅) | `s⁶ + t²` | (not in 5-coef basis) |
| 4 | Parabolic umbilic (D₅) | `s²t + t⁴` | (partial coverage) |

CRYPSOID's 5-coefficient germ basis (`tools/crypsorender/math/germ.py` lines 23–30):

```python
H(s, t) = κ₁·s² + κ₂·t² + χ·(s³ - 3st²) + ω·(3s²t - t³) + ζ·(s⁴ + t⁴)
```

is a parameterization of the linear span of the relevant low-codimension catastrophe normal forms in 2 dimensions. The cubic terms `s³ - 3st²` and `3s²t - t³` are the real and imaginary parts of `(s+it)³` — the **Pearcey caustic generators** (cusp family). The quartic `s⁴ + t⁴` is a swallowtail-related unfolding term. The basis covers the catastrophes of generic codimension ≤ 3 in this dimension regime; higher-codimension germs (butterfly, deeper umbilics) require richer bases.

### 2.3 The invariance statement

**Theorem (right-equivalence is preserved by composition with diffeomorphisms).** Let `f : ℝ² → ℝ` be smooth and let `Φ : ℝ² → ℝ²` be a smooth diffeomorphism. Then `f` and `f ∘ Φ` have right-equivalent germs at corresponding singular points (`p` and `Φ⁻¹(p)`). Equivalently: composing the source map with a diffeomorphism produces another map whose germs are in the same right-equivalence classes as the original.

**Corollary (catastrophe classification survives smooth coordinate change).** The catastrophe type of a singularity (fold, cusp, swallowtail, umbilic, etc.) is invariant under smooth diffeomorphisms of the source plane.

**Proof sketch.** Right-equivalence is itself defined as composition with diffeomorphisms; if `Φ` is a diffeomorphism, then `f` and `f ∘ Φ` are related by `g = ψ ∘ f ∘ φ⁻¹` with `φ = Φ⁻¹` and `ψ = id`. Hence `f ∼_R f ∘ Φ`. Since right-equivalence is by definition the equivalence relation that defines catastrophe classes, the catastrophe class is preserved. □

This is not a deep theorem; it is essentially the *definition* of catastrophe classification. The reason it matters here is that **the natural failure mode of a real camera capture is, to first approximation, exactly such a diffeomorphism**, and so the catastrophe classification of the encoder-placed germs survives the capture. That is the content of the invariance argument.

References: René Thom, *Structural Stability and Morphogenesis* (1972/1989, English ed. Addison-Wesley); V. I. Arnold, *Catastrophe Theory* (3rd ed., Springer 1992); Arnold/Gusein-Zade/Varchenko, *Singularities of Differentiable Maps* (vols I-II, Birkhäuser 1985, 1988); J. Petitot, *Morphogenesis of Meaning* (Peter Lang 2004) for the semiophysics framing.

## 3. Mapping the math claim onto the engineering setup

The engineering setup is:

1. The encoder places germs at positions in a 3D scene. After projection by the rendering camera, each germ corresponds to a singularity of the rendered intensity field at a known 2D location.
2. The rendered intensity field is a smooth map `I_enc : ℝ² → ℝ` (or three smooth maps, one per RGB channel).
3. The display + capture chain composes `I_enc` with several stages:
   - **Display rendering.** The screen converts `I_enc` to emitted light. For an SDR LCD this is approximately a smooth gamma curve; not coordinate-transforming, only intensity-transforming. (See §4.2 for the intensity-transformation case.)
   - **Optical capture.** The phone's camera optics sample the displayed light through a smooth optical transfer function. Geometrically, this corresponds to applying a smooth coordinate transformation `Φ_capture : ℝ² → ℝ²` (the composition of perspective projection, lens distortion, sensor placement) followed by integration over the sensor pixel area.
   - **Sensor sampling.** The continuous captured field is sampled onto the discrete sensor grid. Sub-pixel sampling introduces interpolation that is itself smooth.
   - **Pre-processing pipeline.** White balance, denoising, sharpening, gamma encoding to JPEG. Most of these are smooth intensity-channel transformations; some (sharpening) include slight high-frequency boosts that can affect sub-pixel singularity localization.
4. The decoder receives `I_dec = (pipeline ∘ samples ∘ Φ_capture ∘ display) (I_enc)`.

Under the **smooth diffeomorphism approximation** (the controlling assumption — see §4):

- `Φ_capture` is well-approximated by a smooth diffeomorphism on the carrier's region of the image.
- `display`, `samples`, and `pipeline` together are well-approximated by smooth intensity transformations that do not move singularities to new geometric locations and do not fold or split them.

Under this approximation, the catastrophe germs in `I_enc` (the encoder-placed germs) classify into the same catastrophe types as the corresponding germs in `I_dec` (the decoder-extracted germs), by the corollary in §2.3. The decoder reads the same symbols.

## 4. What the math does not give — the honest limits

This section is critical. The above is true *under the approximation in §3*. The approximation breaks in identifiable, enumerable ways. Each break is a real engineering risk.

### 4.1 Hard discontinuities (occlusion, severe shadow, frame edge)

Right-equivalence by smooth diffeomorphisms presupposes the transformation is *smooth*. Hard discontinuities — a finger partially occluding the carrier, a hard shadow edge from a desk lamp, the carrier extending past the camera frame — are *not* smooth transformations. They introduce new singularities that the encoder did not place and remove germs the encoder did place. The math does not protect against this.

Mitigation: redundant germs (`03_PHOXOIDAL_CARRIER_ARCHITECTURE.md` §5.1) so that the loss of any one germ to occlusion is recoverable by majority vote across the remaining redundant copies. Sheaf-style consistency check (`§5.3`) so that obstruction-detected regions are excluded from the decode.

### 4.2 Severe intensity transformations (extreme dynamic range, clipping, posterization)

A monotone smooth gamma curve does not change germ types. A *non-monotone* or *clipping* transformation can. If a JPEG re-encoder clips highlights to flat white, every singularity inside the clipped region is destroyed (the local map becomes constant; there is no germ). If extreme posterization is applied, smooth fields become piecewise-constant and singularity classification breaks.

Mitigation: encode at intensity levels well inside the carrier-medium's dynamic range (avoid encoding inside the top or bottom 5%); design the Tier C aesthetic field to use mid-gray luminance for the data-bearing region; redundancy across spatially disjoint scene regions.

### 4.3 Adversarial transformations

An adversary who knows the germ classifier and has write-access to the captured image can construct catastrophe-germ-confusable noise that flips germ classifications without doing anything visually salient to a human. This is the steganographic-carrier analog of an adversarial-example attack on a neural network.

This proposal **does not solve adversarial robustness.** Adversarial robustness is a different threat model and is out of scope for both AXP6 (which has the same vulnerability — an adversary can edit AXP6 carrier modules directly) and for the proposed phoxoidal carrier. If the threat model includes adversarial editing, additional cryptographic measures (encrypted payload + signed manifest) are required. `08_HONEST_TRADEOFFS.md` §6.

### 4.4 Extreme scale of transformation

The diffeomorphism approximation degrades as `Φ_capture` becomes extreme. A 5° tilt of the phone is very nearly a smooth diffeomorphism on the carrier region; a 60° tilt of the phone introduces strong perspective foreshortening, motion-induced blur, and sometimes auto-focus failure — all of which compound and the smoothness assumption no longer dominates. The math gives invariance "in the limit"; engineering must specify the regime where the limit is a useful approximation.

Mitigation: characterize the degradation experimentally (Phase 1 work; benchmark against `V2_CAPTURE_PROTOCOL.md` plus a deliberately wider tilt/distance/lighting envelope). Honestly state the carrier's working envelope.

### 4.5 Photon noise and finite SNR

The germ extractor's persistent-homology (or scale-space, or Mumford-Shah) detection is statistical. At low light, photon-counting noise reduces SNR; at low SNR, low-codimension singularities become indistinguishable from noise-induced fake singularities. The decoder's persistence-confidence weighting (`03_PHOXOIDAL_CARRIER_ARCHITECTURE.md` §5.2) helps but does not eliminate the failure mode. Below some SNR threshold, structural decode fails — same as AXP6 fails when the per-block damage exceeds parity recovery capacity.

Mitigation: characterize the SNR vs decode-success curve experimentally. State the working envelope honestly. If extreme low-light is a target deployment regime, additional capture-side measures (longer exposure, stacking) are required.

### 4.6 Discrete sampling at finite resolution

The math assumes a continuous intensity field. Real captures are discrete sensor grids at finite resolution. A germ that is structurally present in the continuous field may be invisible at the sensor's resolution if it is small enough relative to the pixel pitch. The germ extractor must operate at a scale appropriate to the sensor; very-small germs are below detection threshold by Nyquist.

Mitigation: choose germ scales and scene resolution so that each germ projects to ≥ k sensor pixels for some k (Phase 1 must measure the right k; rough first guess from `05_INFORMATION_DENSITY_ANALYSIS.md` is ~5×5). This sets a floor on the carrier's pixel resolution as a function of scene germ density.

### 4.7 Higher-order catastrophes outside the 5-coefficient basis

CRYPSOID's basis (`tools/crypsorender/math/germ.py`) covers fold, cusp, hyperbolic/elliptic umbilic, and partial swallowtail. It does not cover butterfly (A₅), wigwam (A₆), parabolic umbilic (D₅) fully, or any of the higher singularities. If natural image content (the Tier C aesthetic field) contains higher-codimension singularities, they will be misclassified by the 5-coef extractor.

In practice this matters less than it sounds: real natural images are dominated by codimension ≤ 2 singularities (folds and cusps from object boundaries, edges of shadows); butterfly and deeper germs are rare. But "rare" is not "zero," and a Tier C field containing such germs will introduce decode noise. Mitigation: design Tier C fields to avoid high-codimension singularities, or extend the basis (Phase 2+ work).

### 4.8 Composition of effects

The §4.1 through §4.7 limits compose. A capture in low light, at high tilt, with a finger occluding 10% of the carrier, with a JPEG re-encoder clipping highlights, of a Tier C field containing a butterfly singularity, will fail in many independent ways. Each failure mode is mitigable individually; the composition has fewer mitigations than the sum of the parts, because mitigations consume each other's redundancy budget.

The honest framing: **diffeomorphism invariance gives a substrate that is structurally robust to capture-mediated transformations under a stated approximation. The approximation is well-justified for the bright-clean-static-handheld-near-axis regime that V2's capture protocol targets, and degrades smoothly outside that regime.** Whether the degradation outside V2's protocol is acceptable for the intended deployment is a workflow question, not a math question (`09_OPEN_QUESTIONS.md` §2).

## 5. The geometric position of germs is not preserved (and that's OK)

A subtle but important point: diffeomorphism invariance preserves the *catastrophe class* of a germ at a singularity, but it *moves the singularity to a new geometric location*. A fold at position `p` in `I_enc` is a fold at position `Φ_capture(p)` in `I_dec`, not at `p` itself.

For the proposed carrier this is fine, because the **symbol decoding is keyed on germ classification, not on germ position**. The decoder reads the catastrophe type and the 5-coefficient values of each detected germ, not its image-plane position. The order in which germs are read can be recovered from the manifest cluster (`03_PHOXOIDAL_CARRIER_ARCHITECTURE.md` §7), which itself is a known-shape germ cluster identifiable structurally rather than positionally.

The position-mobility of germs is in fact part of why the approach works: a perspective tilt that moves every germ to a new image-plane location does not move them to *unknown* image-plane locations from the decoder's perspective; it moves them to image-plane locations that the decoder finds via structural detection. The decoder never needs to know "germ #471 was at pixel (3201, 8442)"; it needs to know "the 6,000,000-th germ in canonical decode order has these coefficients."

This is the inversion of AXP6's logic: AXP6 reads modules at known positions and tolerates value-noise; the phoxoidal carrier reads classified structure at *unknown* positions and tolerates positional warp. The two architectures defend against orthogonal failure regimes.

## 6. A concrete example to ground the abstraction

Consider the simplest non-trivial case: an encoder places a single cusp germ (A₃, normal form `H(s,t) = ζ(s⁴ + t⁴)` with say `ζ = 1.0`) at scene position `(0, 0, 0)` viewed by a rendering camera at `(0, 0, -10)` looking toward `+z`. The rendered image is a smooth intensity field with one cusp singularity at the projected location of the scene origin.

The display shows this image. The phone camera, tilted 5° forward, captures it. The captured image's intensity field is a slightly perspective-distorted version of the original.

Apply the germ extractor:
- Persistent homology identifies a topological feature at scale `σ` matching the expected cusp footprint.
- Mumford-Shah variational fitting locates the singular point to sub-pixel precision.
- Local neighborhood fitting computes a 5-coefficient germ in a canonical local frame at the detected singular point.

The recovered germ has approximately `ζ ≈ 1.0` (within detection noise) and other coefficients near zero. The cusp class is recovered. The position of the singularity is at the perspective-distorted location of the original scene origin, which the decoder does not need.

If a second cusp is placed nearby with a different `ζ` (say `ζ = -1.0`), the encoder is reading "two cusps with opposite-sign quartic coefficients" → some specific bit pattern. The decoder reads the same.

Add a thousand germs. Add Tier C aesthetic background. Add a real S23 Ultra capture under V2 protocol conditions. The argument is the same: the catastrophe types and coefficient values of the germs are read from the captured field, not from any pixel-coordinate addressing scheme. The capture warp moves germs around in the image plane; it does not change their classification.

This is the architecture's reason to exist.

## 7. Summary

The math gives:
- ✅ Invariance of catastrophe classification under smooth diffeomorphisms of the source plane.
- ✅ A finite list of generic singularity types whose normal forms are well-tabulated and computable.
- ✅ A structural reason that pixel-grid encodings (which depend on integer coordinate addressing) are not invariant under capture warp, while germ-classification encodings are.

The math does not give:
- ❌ Robustness to non-smooth transformations (occlusion, hard discontinuities).
- ❌ Robustness to adversarial transformations.
- ❌ Robustness to extreme intensity transformations (clipping, posterization).
- ❌ Robustness to extreme tilt/distance/lighting where the smooth approximation degrades.
- ❌ Detection at sub-Nyquist resolution.
- ❌ Coverage of higher-codimension catastrophes outside the 5-coefficient basis.

The engineering job (`06_DECODER_RESEARCH_PLAN.md`) is to build a decoder that lives in the regime where the math gives the architecture's claimed invariance, and to characterize honestly where that regime ends. The math does not promise the engineering will be easy. It promises only that the regime exists and is structurally well-defined.

---

**Cross-references.** The architecture that depends on this math is in `03_PHOXOIDAL_CARRIER_ARCHITECTURE.md`. The decoder research that lives in the regime where the math holds is in `06_DECODER_RESEARCH_PLAN.md`. The engineering tradeoffs the math does not dissolve are in `08_HONEST_TRADEOFFS.md`.
