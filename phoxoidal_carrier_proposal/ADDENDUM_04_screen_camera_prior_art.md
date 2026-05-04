# Addendum 04 — Screen-Camera Prior Art Survey (post-spike-8B)

**Status:** Phase 1 research-pass output (informational; informs P3 sequel decisions)
**Authored:** 2026-05-04
**Authorized by:** Bug, after spike-8B run 1 (phone-on-phone, 0/8 inner decode despite 6/8 pose success) and runs 2-3 (Asus laptop, blocked on display setup).

This addendum records the result of a focused literature pass on screen-camera-robust steganographic carriers, run because spike-8B's failure mode (high-frequency moiré stamped onto rectified germ patches; 5-coefficient solver biased toward wrong codebook entries) suggested our substrate may have a known-and-solved channel-mismatch problem.

---

## 1. Headline finding

The prior art has a clear, near-unanimous answer to the spike-8B failure mode, and it contradicts our substrate choice: **subtle continuous-grayscale spatial modulation at amp ≈ 0.30 is exactly the regime that the screen-camera channel destroys**.

Every successful screen-camera-robust system in the last decade either:
- (a) goes high-contrast and discrete (QR / AprilTag class), or
- (b) uses temporal/alpha modulation that exploits vision-vs-camera frame-rate asymmetry (HiLight, InFrame, VRCodes), or
- (c) trains an end-to-end neural codec against a differentiable distortion stack containing the exact moiré/JPEG/blur perturbations that just killed our decode (StegaStamp, LFM, Fang-2018, RIHOOP, the 2023–2025 DCT-attention family).

Our analytic catastrophe-germ codebook is mathematically beautiful and is a perfectly reasonable substrate for a *digital* channel — but it has no built-in defense against the dominant noise mode of the *display→optics→Bayer→demosaic→JPEG* pipeline, which is precisely the high-frequency striping observed in spike-8B run 1.

## 2. State of the art

**StegaStamp (Tancik, Mildenhall, Mildenhall, Ng — CVPR 2020)** is the closest analog to what we're trying to do. They embed 100 bits per 400×400 image (~0.625 bits/px raw, ECC-reduced to 56 useful bits) and report **99.4% bit accuracy on cellphone-captured laptop screens** and 99.0% on print. They train a U-Net encoder against a *differentiable distortion stack* containing perspective warp ±10%, motion blur 3–7 px, Gaussian blur σ ∈ [1,3], per-channel color offset ±0.1, brightness/contrast affine, Gaussian noise σ ∈ [0,0.2], JPEG quality ∈ [50,100]. The encoder learns to put information into spatially-distributed mid-frequency residuals robust to all these *simultaneously* — and authors note residual artifacts show up in low-frequency regions, meaning the learned code is *not* primarily low-frequency.

That is the single most important contrast with our germ design: we put information in the smooth low-frequency polynomial coefficients, which moiré stripes alias directly into.

**Light Field Messaging (Wengrowski & Dana, CVPR 2019)** is the screen-camera-specific predecessor. Their core construct is the *Camera-Display Transfer Function (CDTF)*, learned from a 1M-image dataset across 25 camera/display pairs, modeling spectral emittance, sampling, gamma, and color crosstalk as a single learned operator. Their qualitative claim — that hand-designed channel models systematically underestimate screen-camera distortion — is now consensus.

**Fang et al. 2018 ("Screen-Shooting Resilient Watermarking", IEEE TIFS)** and 2023–2025 follow-ups (DoBMark, Cross-Attention 2025, lightweight DCT-frequency, RoPaSS for partial capture, Grayscale-Deviation-Simulation TMM 2024) converge on a recipe: **8×8 DCT blocks, mid-frequency band embedding, plus a noise layer that explicitly simulates moiré + lens distortion + illumination + perspective + Gaussian noise**. Mid-band is the sweet spot: low-band kills imperceptibility, high-band is exactly what Bayer/demosaic/JPEG eat. Recent work reports >95% extraction across angles and distances. *Every* successful method since 2020 includes a moiré simulation step in training — our decoder has no such defense.

**HiLight (Li et al., MobiSys 2015), InFrame/InFrame++ (Wang et al., MobiSys 2014–15), VRCodes (Woo, Lippman, Raskar 2012), PixNet** are the temporal/alpha family. They sidestep the spatial-frequency problem by exploiting flicker-fusion (>60 Hz invisible to humans, fully visible to cameras) and rolling shutter. None apply to a static PNG carrier — but they tell us the field considers static spatial-grayscale embedding *the hardest case*, and that's the case we've chosen.

**QR / AprilTag / ArUco** survive screen-camera roundtrips because (a) modules are large, binary, and high-contrast — there is no continuous quantity for moiré to bias; (b) Reed-Solomon block-interleaved ECC tolerates burst errors from local moiré bands; (c) finder/alignment patterns are spatially separated from data; (d) AprilTag's lexicode design guarantees minimum Hamming distance under all rotations. We borrowed (a)+(c) for the fiducial layer but borrowed (b) only as a byte-stream RS *after* the per-germ continuous-coefficient decision has been made. **The ECC can't fix a coefficient-fitting bias.**

**Information-theoretic framing.** Imatest/Koren-style analysis suggests modern phone cameras at typical screen-capture distances yield ~2–3 bits per pixel of usable channel capacity *on the original sensor* — but after optical MTF, demosaic, JPEG, and the screen's own subpixel raster, the effective capacity in the spatial-grayscale band our germs occupy drops by 1–2 orders of magnitude. StegaStamp's 0.625 bits/px is roughly the empirical ceiling for static print/screen-camera with neural encoding; our design at 8 bits per 25×25 patch = ~0.0128 bits/px is well under that ceiling, so density isn't the issue — **channel matching is.**

## 3. Concrete substrate-design recommendations for P3.A (ranked by impact-to-effort)

1. **Drop the continuous 5-coefficient codebook; quantize to a discrete per-germ symbol set.** Replace "fit 5 real coefficients then nearest-codeword-in-256" with "render N visually-distinguishable discrete germ shapes and classify". With N=16 (4 bits/germ) and 600 germs we keep 2400 bits raw → ~1500 bits post-RS, still plenty for AXP6+SHA. A discrete classifier is robust to moiré in a way least-squares fitting fundamentally is not. **Highest impact, ~1–2 days work.**

2. **Bandpass the decoder's per-germ feature, don't just Gaussian pre-blur.** The moiré is a narrow vertical-stripe band around the screen-subpixel-vs-Bayer beat frequency. A directional notch filter (or a 2D Butterworth bandpass tuned to the germ's intrinsic spatial scale of ~5–8 px periods inside the 25-px patch) will kill stripes without erasing the germ. Pre-blur σ=3 on a 25-px patch is too aggressive — it eats signal. **High impact, half-day.**

3. **Increase amp from 0.30 toward 0.6–0.8, not 1.0.** amp=0.30 is in the regime where moiré amplitude (typically 5–15% luminance after demosaic+JPEG) is comparable to the signal. amp=1.0 saturates and destroys the sigmoid forward model's analytic invertibility. amp ≈ 0.6–0.7 keeps the sigmoid in its responsive range while pushing germ signal ~3–5× over the dominant noise floor. Pair with #1 and #2. **Medium impact, trivial.**

4. **Move the per-germ payload into a 2D mid-band DCT of the 25×25 patch, not the spatial polynomial coefficients.** The entire screen-shooting watermarking literature converges on 8×8 mid-band DCT for a reason: it is exactly the band that survives the channel. Keep the catastrophe-germ *visual aesthetic* by using the polynomial as a *cover image* and embedding 4–8 bits in mid-band DCT coefficients of the patch via QIM or differential modulation. **High impact, 2–3 days.**

5. **Add a moiré-simulation pass to the validation harness.** Render carrier → apply screen-subpixel raster (RGB stripe mask) → 2× upsample → apply Bayer mosaic with a random sub-pixel offset → bilinear demosaic → JPEG q=70–85 → downsample → 1.5× perspective warp → Gaussian noise σ=0.02. If the decoder doesn't pass *that*, it cannot pass real capture. **Highest leverage for catching regressions, 1 day.**

6. **Color (RGB) is a real lever we haven't used.** Phone-camera Bayer arrays are 50% green, 25% R, 25% B. Embedding redundantly across channels with channel-specific weighting (heavier on G) gives 2–3× SNR for free. Trade-off: breaks the "grayscale phoxoidal" aesthetic. **Medium impact, ~1 week.**

7. **A neural encoder/decoder is *not* the only path, but it is the empirical state of the art at high density.** StegaStamp's 99% BER at 100 bits / 400² is the bar; nothing analytic published comes within 5× of that under arbitrary-pose capture. If we want to keep the analytic-substrate philosophy, accept operating at 5–10× lower density than neural codecs and design for that. **High effort, deferrable until #1–#5 are exhausted.**

## 4. Blind spots in the current framework

- **No channel model in the substrate design.** The catastrophe-germ family is derived from singularity theory, not from the screen-camera channel's transfer function. Mathematical naturalness ≠ alignment with the channel's null-space.
- **LSQ coefficient fitting is the wrong decoder for a noisy channel.** It is BLUE only under additive Gaussian noise on the *coefficients*, which is not the noise model — moiré stripes are *structured, multiplicative, spatially-correlated* perturbations of the *image*, projecting onto the polynomial basis with a non-zero, non-random mean. We need either a discriminative classifier, a robust M-estimator (Huber/Tukey), or a channel-aware whitening pre-step. We have none.
- **No empirical channel calibration beyond 4 photometric pilots.** Four pilots fit `a + b·I^γ` — a 3-parameter pointwise model. They cannot capture the *spatial* (moiré, MTF rolloff) or *spectral* (chroma crosstalk, demosaic) components of the channel. Pilot-fit success is misleading: it told us the *photometric* channel is identifiable, while saying nothing about the *spatial-frequency* channel that actually killed the decode.

## 5. Recommended next spike

**Spike-9A — synthetic screen-camera distortion harness (one day, no hardware needed):** Build the synthetic screen-camera distortion pipeline from recommendation #5 (subpixel-raster → Bayer → demosaic → JPEG q=80 → mild warp + noise) and run it on the existing carrier. If the existing decoder fails synthetically the way it failed on spike-8B, we have a closed-loop test bed. Then, on that test bed only, swap the 256-codeword continuous LSQ decoder for a 16-symbol discrete germ classifier (recommendation #1) tuned on synthetically-distorted germs. If 16-way discrete decoding clears, say, >90% on the synthetic channel where 256-way continuous clears 0%, we have validated the central hypothesis (channel-mismatch, not insufficient ECC) and earned the right to a spike-9B on real hardware.

The fastest way to confirm or deny "are we fundamentally suboptimal for this channel" is a half-day of synthetic-distortion plumbing — not another phone-on-phone capture session.

## 6. Sources

- StegaStamp: Invisible Hyperlinks in Physical Photographs (Tancik et al., CVPR 2020) — arXiv 1904.05343
- Light Field Messaging with Deep Photographic Steganography (Wengrowski & Dana, CVPR 2019)
- HiLight (Li et al., MobiSys 2015); InFrame++ (Wang et al., MobiSys 2015); VRCodes (Woo et al., 2012)
- Screen-Shooting Resilient Watermarking (Fang et al., IEEE TIFS 2018) + 2023–2025 follow-ups
- Universal screen-shooting robust image watermarking with channel-attention in DCT domain (ESWA 2024)
- Screen-Shooting Resistant Watermarking With Grayscale Deviation Simulation (IEEE TMM 2024)
- RoPaSS: Robust Watermarking for Partial Screen-Shooting (AAAI 2024)
- AprilTag 2 (Wang & Olson, IROS 2016); AprilTag (Olson, ICRA 2011)
- Imatest / Koren camera information capacity analyses; Imatest color moiré reference
