# Spike-8B real-camera validation report

**Timestamp:** 20260504T16xxxxZ
**Substrate under test:** P3.A (ArUco fiducials + spike-7 codebook)
**Reference payload SHA-256:** `12265155a5ade7abfa1a9f30702fbd47ffb7dcedd1cc009f2d73195f3423a7a0`

## Captures

8 captures, alternate-test setup:
- **Source display:** a phone screen (NOT a monitor) showing `reference_carrier.png`
- **Camera:** another phone (suspected S21 FE)
- **Conditions:** "comfy" distance, ~head-on, carrier rotated 90° in frame
  (camera-phone landscape vs source-phone portrait), bright/mixed lighting

## Headline

**0/8 PASS — but the failure mode is highly informative.**

| Layer | Result | Detail |
|---|---|---|
| ArUco pose recovery | **6/8 succeeded** | 2 captures: only 3 of 4 markers detected (75% pose-layer success rate in real-world phone-on-phone capture) |
| Pilot intensity-transform fit | **6/6 succeeded** | reasonable transforms recovered: γ ≈ 0.79-0.89, b ≈ 0.50-0.85, a ≈ +0.15-+0.40 |
| Manifest-magic decode | **0/6 matched `PHX1`** | best partial match: 2 of 4 magic bytes (positions 0 and 3) decode correctly under heavy Gaussian pre-blur |

**This is not a fundamental architectural failure.** The pose layer mostly works.
The pilots fit reasonable photometric transforms. The catastrophe-germ codebook
nearest-neighbor decoder fails — and we now have a precise diagnosis of why.

## Root cause: screen subpixel moiré

Side-by-side comparison of the manifest region (`debug_manifest_zoom_01.png`):

- **LEFT (canonical):** smooth catastrophe-germ patches with the subtle low-frequency
  gradient structure the codebook is trained on.
- **RIGHT (rectified capture):** each germ patch has the *correct overall shape*
  but with **sharp high-frequency vertical stripes** stamped onto it. These come
  from the source-phone screen's RGB subpixel layout, captured by the camera's
  Bayer-pattern sensor, demosaiced and converted to grayscale.

The 5-coefficient catastrophe-germ solver fits least-squares against the patch.
The right 5 coefficients describe the smooth gradient — but the high-frequency
moiré is *also* something the solver tries to fit. The result: 5-coefficient
estimates biased away from the true codeword toward wrong codebook entries.

**Sanity check via Gaussian pre-blur experiment:**

Re-decoding rectified captures with various σ Gaussian smoothing (results
abridged for capture 1):

```
σ=0.0: magic=27141031   (0/4 magic bytes match)
σ=0.5: magic=1b141031   (0/4)
σ=1.0: magic=271410a7   (0/4)
σ=1.5: magic=50a810a7   (1/4: byte 0 = P)
σ=2.0: magic=50a81070   (1/4)
σ=3.0: magic=50a81031   (2/4: bytes 0 + 3 = P, 1)
```

Heavier blur recovers the LOW-frequency catastrophe gradient by attenuating the
high-frequency moiré. Two of four magic bytes recover at σ=3.0; recovery
remains partial because (a) the carrier was displayed at non-1:1 pixel resolution
on the source phone, so additional content is lost, and (b) σ=3.0 also blurs out
some legitimate germ structure the solver needs.

## What this means

- **Substrate architecture is sound.** Pose layer + photometric calibration both
  work in real-world capture. The diagnosis is at the solver layer's robustness
  to a specific real-world artifact (screen-display moiré) we didn't model
  synthetically.
- **The phone-on-phone capture path is fundamentally lossy** in a way the
  synthetic noise tests didn't predict. Two stacked LCD/OLED panel resolutions
  + two stacked Bayer demosaics = high-frequency cross-talk that masks germ
  structure.
- **The synthetic envelope underestimated photometric drift.** Pilot fits show
  a ≈ +0.30, well outside the ±0.10 brightness range the synthetic gate tested.
  The pilots correctly compensated, so this isn't a failure mode — but it
  confirms the calibration layer is doing real work in the wild.

## Recommendation

**Don't conclude "P3.A is broken."** Conclude "phone-on-phone capture is broken."

Next step: **try the same captures on a real monitor** (MSI G27C4X 1440p or
Asus laptop), where:
- The carrier displays at near-native pixel resolution
- The screen pixel pitch is much smaller than the camera-captured per-germ
  area, so moiré is suppressed by averaging
- The high-frequency subpixel structure won't dominate the catastrophe-germ
  fits

If P3.A decodes cleanly on a real monitor → the takeaway is a **deployment
requirement** ("V1 carriers are designed for monitor display, not handset
display"). This is reasonable for a steganographic carrier format and
parallels how QR codes work in practice.

If P3.A also fails on a real monitor → there's a deeper substrate brittleness
to investigate (likely solver-level moiré rejection or codebook-design issues).

## Optional next-iteration mitigations (only if monitor test ALSO fails)

These would extend P3.A's solver layer:

1. **Adaptive low-pass filter** in the decoder before sampling germs.
   Estimate the dominant noise frequency in the rectified image (e.g., from
   FFT analysis of the gray surround), apply a notch filter at that frequency.
2. **Frequency-domain solver** that fits the 5 catastrophe coefficients
   weighted toward LOW spatial frequencies, explicitly de-weighting
   high-frequency content.
3. **Re-design the codebook** with redundant high-frequency content to
   distinguish real germ structure from moiré.

Each is a multi-day spike; none should be authorized until we confirm the
monitor test result first.

## Files in this report

- `results/spike8b_results.json` — per-capture machine-readable results
- `results/debug_rectified_01.png` — full rectified frame for capture 1
- `results/debug_reference_vs_rectified_01.png` — side-by-side full carrier
- `results/debug_manifest_zoom_01.png` — side-by-side manifest region (the
  smoking gun: subpixel moiré on real germs)

## Solo decision-tree outcome

Per `CAPTURE_PROTOCOL.md`:
- 0/8 falls into the **<4/9 PASS bucket**: "P3.A has a real-world brittleness
  we didn't predict. Investigate before any further captures."
- The investigation above identifies the brittleness specifically as
  display-pathway-dependent. The recommended next experiment (MSI/Asus monitor
  display) is exactly the targeted next step that will tell us whether to
  block, mitigate, or document-as-deployment-requirement.
