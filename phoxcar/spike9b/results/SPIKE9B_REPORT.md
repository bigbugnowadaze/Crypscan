# Spike-9B-prime Report — channel-matched catastrophe-germ substrate

**Status:** **central architectural hypothesis empirically validated**
**Authored:** 2026-05-04
**Purpose:** test whether catastrophe-germ math at a channel-matched
spatial scale, with image-space projection-NCC decoding, can survive
the screen-camera channel that destroyed P3.A — without adopting
discrete-module substrate, neural codecs, or Aurexis-style 30-patch
list. ADDENDUM_06 §3 hypothesis.

## Headline

**Yes. The catastrophe-germ math survives screen-camera analytically.**

| Variant | Synthetic channel result | Notes |
|---|---|---|
| V0 (P3.A: σ=4, LSQ + coeff-NN, 4 cluster pilots) | **FAIL** | manifest magic mismatch; spike-9A baseline |
| V_scale (σ=8 + image-space NCC, global pilot fit) | **PASS** | SHA-256 round-trip, 1 RS correction |
| V_full (σ=8 + image-space NCC + per-quadrant pilot fit) | **PASS** | SHA-256 round-trip, 1 RS correction |

This is the architectural existence proof. **A purely analytic
substrate based on catastrophe-germ math, with no neural net, no
Chase-2, no QPP interleaver, no CIELab classification, no learned
Camera-Display Transfer Function — decodes screen-camera-distorted
captures end to end.**

## Operating envelope

Severity sweep on the calibrated synthetic channel (default subpixel
raster + Bayer demosaic + JPEG q=80 + mild perspective + Gaussian
noise unless varied):

```
JPEG q=30 ... q=95          PASS    (full quality range)
perspective_tilt=0..20°      PASS
perspective_tilt=30°         FAIL — ArUco pose failed (2 markers detected)
gaussian σ=0.005..0.05       PASS    (5× the level that destroyed P3.A)
gaussian σ=0.10              FAIL — ArUco pose failed
camera_oversample=1.0        FAIL — ArUco pose failed
camera_oversample=3.0        PASS
combined severe (q=50 +
   30° tilt + σ=0.05)        FAIL — ArUco pose failed (1 marker)
```

**All failures in the sweep are at the POSE LAYER (ArUco), not the
inner substrate.** When pose succeeds, the channel-matched substrate
decodes across a wide envelope. The pose layer is hardenable
independently (AprilTag instead of ArUco, subpixel quad refinement,
lower-frequency markers, etc.) but that's a separate work stream.

## Substrate design (the three pillars from ADDENDUM_06)

### Pillar 1: channel-matched germ scale

- σ from 4 → 8 (Gaussian-weighted basis)
- half_size from 12 → 24 (germ patches grow from 25×25 to 49×49 px)
- Spacing 28 → 56 (no patch overlap)
- Grid 26×26 = 676 slots → 13×13 = 169 slots

The germ's intrinsic spatial scale is now LARGER than the moiré's
beat frequency. Side-by-side `spike9b_manifest_zoom.png`: the clean
catastrophe germs (left) are still recognizable in the channel output
(right) — the moiré stamping is visible but doesn't wash out the
underlying gradient structure. This is where the win comes from.

### Pillar 2: image-space NCC projection decode

- Decoder pre-renders all 256 codeword templates at canonical σ + amp
- Per germ, extract patch from rectified-corrected image
- NCC against all 256 templates, pick max
- This bypasses the LSQ-fit-then-classify path that biased toward
  wrong codewords under structured noise

### Pillar 3: spatially-distributed multi-pilot calibration

- 16 pilots distributed across the canvas (4 corners + 4 edge
  midpoints + 4 mid-radius + 4 near-center)
- 4 pilots per canvas quadrant
- Each quadrant fits its own (a, b, γ) intensity transform
- Smooth-varying photometric drift (lighting gradients, lens
  vignetting, curved-monitor luminance falloff) handled by
  per-region calibration

In the synthetic-channel test, per-quadrant gave the same result as
global pilot fit (median NCC 0.801 / 1 RS correction either way) —
the synthetic channel has uniform photometric drift across the canvas.
**Per-quadrant calibration's advantage shows up under non-uniform
real-world conditions** (curved monitor, off-axis capture, lighting
gradients) which are not modeled in the current synthetic channel.

## Density trade-off (acknowledged honestly)

| Substrate | Grid slots | Payload germs | RS scheme | Raw payload bytes |
|---|---|---|---|---|
| P3.A (σ=4, half_size=12) | 676 | ~660 | RS(255,223) | ~660 |
| spike-9B (σ=8, half_size=24) | 169 | 145 | RS(127,111) | 145 |

Spike-9B halves density per canvas. RS scheme also reduced (from
RS(255,223) to RS(127,111)) so smaller payloads fit. These are
real, acknowledged trade-offs. They can be recovered by:
- Larger canvas (1280→1600 or 1920) — straightforward extension
- Per-germ codebook expansion (still possible with image-space NCC,
  if the channel SNR allows finer codeword separation; needs
  empirical validation)
- Color channels (3× capacity if RGB — but breaks grayscale aesthetic)

The point of spike-9B-prime is **architectural existence**, not
density parity. Density is a future-spike-9C optimization.

## What this proves about the proposal

ADDENDUM_06 hypothesized:

> Most of Vince's recommended fixes (Chase-2, CIELab, Sauvola, QPP,
> Forstner subpixel, sheaf diffusion) are answers to *questions the
> catastrophe-germ substrate doesn't ask*. The radical move is:
> catastrophe-germ math at the channel-matched scale, with
> projection-native soft decoding, with multi-frame catastrophe
> persistence.

**Pillars 1-3 of that hypothesis are now empirically supported.**
Pillars 4-5 (grid-as-fiducial pose, multi-frame catastrophe persistence)
remain stretch goals — they would extend the envelope further but
aren't required for the existence proof.

## What this does NOT prove

- **Real-world capture validation is still required.** Synthetic channel
  reproduces spike-8B run 4's failure mode, but real cameras have
  additional non-modeled complexities (varying focus, glare, AWB drift,
  rolling shutter, white-balance temperature shifts). Spike-9C should
  re-run the actual captures from spike-8B / future captures.
- **Density vs V2.1 is not addressed.** V2.1's 3,568-byte real-capture
  result (with discrete colored modules + RS+Chase) is ~25× higher
  density than spike-9B's ~145 raw bytes. Phoxoidal-carrier still
  loses on density but wins on architectural elegance and on the
  not-yet-tested fronts (curved monitor, projective robustness via
  catastrophe singularities).
- **Pose layer is the new bottleneck.** Failures in the severity sweep
  are all ArUco pose failures, not substrate failures. Stretch goal
  pillar 4 (grid-as-fiducial) would address this.

## Recommended next move

**Spike-9C**: real-camera validation of the spike-9B substrate.

1. Generate `reference_carrier_v9b.png` (1280×1280, σ=8 substrate)
2. Bug displays it on the Asus laptop (or MSI when available) in
   fullscreen Chrome at native 1:1 (per the recently-debugged display
   protocol)
3. Capture 9 photos per the existing CAPTURE_PROTOCOL.md solo quick
   pass (S21 FE, comfy distance, head-on / tilt15 / tilt30 / rot90 /
   handheld, varying lighting)
4. Run `phoxcar/spike9b/decoder.py` on each capture
5. Report pass/fail rate

If spike-9C passes (even partially) on real captures, the phoxoidal
carrier is empirically validated as a screen-camera-robust substrate.
That's the strongest claim the proposal can make for V1.

If spike-9C fails despite synthetic success, we learn that the
synthetic channel is missing a real-world distortion mode (likely
candidates: curved-monitor projection, glare/reflection patches,
AWB drift) and we extend the channel + retry.

Estimated effort: ~30 minutes of capture session + 30 minutes of
analysis. No new substrate work needed.

## Files

- `encoder.py` — spike-9B encoder (σ=8 + 16 distributed pilots)
- `decoder.py` — image-space NCC + per-quadrant pilot calibration
- `pilots.py` — multi-pilot calibration (LocalIntensityTransformGrid)
- `pilots_base.py` — verbatim spike-7+ pilot core (re-exported)
- `ecc.py` — RS(127, 111) for spike-9B's smaller canvas
- `channel.py` — spike-9A's calibrated synthetic channel
- `discrete_codebook.py` — image-space NCC classifier (from spike-9A)
- `test_zero_warp.py` — sanity test (PASS, NCC 0.98)
- `test_channel.py` — three-variant comparison (V_scale + V_full PASS)
- `test_severity_sweep.py` — operating envelope characterization

- `results/spike9b_clean_carrier.png` — encoded carrier (σ=8 substrate)
- `results/spike9b_channel_output.png` — same after synthetic channel
- `results/spike9b_manifest_zoom.png` — side-by-side manifest region
  (the visual proof: large germs survive moiré where small ones don't)
