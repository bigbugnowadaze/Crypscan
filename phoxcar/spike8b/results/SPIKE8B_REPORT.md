# Spike-8B real-camera validation report

**Timestamp:** 20260504T16xxxxZ (run 1: phone-on-phone), 20260504T17xxxxZ (run 2: Asus laptop)
**Substrate under test:** P3.A (ArUco fiducials + spike-7 codebook)
**Reference payload SHA-256:** `12265155a5ade7abfa1a9f30702fbd47ffb7dcedd1cc009f2d73195f3423a7a0`

## Executive summary

Two capture sessions, two different failure modes — neither yet confirms or
disproves the production envelope. Both surface real-world issues we did not
predict from synthetic tests.

| Run | Display | Captures | Pass | Failure mode |
|---|---|---|---|---|
| 1 | phone screen (S21 FE-ish) | 8 | 0 | pose 6/8, inner decode 0/6 — **screen subpixel moiré** breaks codebook NN |
| 2 | Asus laptop screen | 9 | 0 | pose 0/9 — **carrier display issue** (markers stretched/distorted/half-cropped) |

**Run 2 does NOT yet test "carrier on a real monitor."** The Asus display itself
appears to have rendered the carrier wrong (germ field fills only the top half
of the carrier in the rectified-cropped view; markers are too small or non-square
for ArUco). One more attempt with a known-correct display setup is needed before
we can declare anything about the monitor pathway.

---

## Run 1: phone-on-phone (8 captures, 2026-05-04 ~16Z)

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

---

## Run 2: Asus laptop screen (9 captures, 2026-05-04 ~17Z)

Bug attempted the recommended next step (display reference_carrier.png on the
Asus laptop), but the captures surface a **different problem entirely**: the
display itself didn't render the carrier correctly. Pose recovery fails on
all 9 because the markers in the photographed frame are not recognizable as
ArUco markers.

| Layer | Result |
|---|---|
| ArUco pose | **0/9** — 8 captures: 0 markers detected; 1 capture: 1 marker (with wrong ID=28) |

### What the captures show

Side-by-side `debug_asus_vs_reference.png` (canonical reference vs cropped
Asus capture):

- **Reference (left):** 4 large ArUco markers at corners; germ field fills the
  central 56% of the canvas; aspect 1:1 throughout.
- **Asus capture (right):** 4 small markers at the corners of a square gray
  region; germ field fills only the **top half** of that region (or only the
  left half before un-rotating); bottom half shows screen surface with
  smudges/glare and faint moiré.

This means **the carrier was not displayed at full canonical resolution +
aspect ratio on the laptop screen.** Possibilities:

1. **Carrier displayed at non-1:1 aspect ratio.** If the image viewer rendered
   the carrier with vertical compression (or horizontal stretch), the markers
   become non-square rectangles and ArUco rejects them by design.
2. **Carrier displayed with letterbox/crop, with the bottom 2 "markers" being
   screen artifacts** (dust, dead pixels, edge of a window/panel) that aren't
   real markers.
3. **Window viewer showed only top half of the carrier** with the bottom-half
   space occupied by viewer chrome / desktop background.

In all cases, the issue is upstream of the substrate — neither pose nor inner
decode gets to run because the displayed image isn't a faithful render of
reference_carrier.png.

### What this tells us

**Run 2 is NOT a P3.A failure**, it's a display-setup failure. We have no
data yet on whether P3.A works against a properly-displayed monitor carrier.

### Recommended next attempt (run 3)

Display the carrier on the Asus (or MSI) **explicitly at 1:1 native pixel
resolution**, with the carrier filling most of the photo when captured. One of:

- **In a browser:** open `reference_carrier.png` directly via `file://` URL.
  The browser will display it at native resolution (1280×1280 actual pixels).
  Zoom-to-fit or scroll-to-center if needed.
- **In Windows Photos / Image Viewer:** open the file, set zoom to "Actual
  size" or 100% (NOT "fit to window" if the window aspect is non-square).
- **Full-screen slideshow mode:** in many viewers, F11 / right-click →
  "View full screen" gives you a black surround and 1:1 actual-size display.

**Critical sanity-check before capturing:** look at the displayed carrier on
the screen. The 4 ArUco corner markers should appear as visibly-square
high-contrast tiles. If they look stretched (rectangles) or tiny relative to
the carrier interior, the display is wrong.

Then capture per the existing protocol (close enough that the carrier fills
60-80% of the photo frame; head-on; bright lighting). 9 captures is fine; even
1 successful decode would be a strong signal.

## Files in run 2

- `results/debug_asus_cropped_01.png` — auto-cropped Asus capture
- `results/debug_asus_vs_reference.png` — side-by-side canonical vs Asus cropped
- `results/debug_clahe_05.png` — CLAHE-contrast-enhanced version (also failed
  ArUco; not a contrast issue)

---

## Run 4: Asus laptop, properly-displayed (3 captures, 2026-05-04 ~19Z)

After Bug verified the file integrity and re-displayed `reference_carrier.png`
in fullscreen Chrome (F11) at native 1:1 resolution, three more captures from
the S21 FE.

| Layer | Result |
|---|---|
| ArUco pose | **3/3 succeeded** — markers correctly detected, all canonical IDs found |
| Pilot intensity-transform fit | succeeded for all 3 |
| Manifest-magic decode | **0/3 matched `PHX1`** — same failure mode as run 1 (codebook NN returns wrong bytes) |

### Magic byte analysis

```
Expected:  50485831  (PHX1 = P, H, X, 1)
Cap 01:    911658b6  byte 2 (X) ✓; rest wrong
Cap 02:    1b160fb6  none correct
Cap 03:    1b1658b6  byte 2 (X) ✓; rest wrong
```

Different per-capture errors, same structural failure: per-germ codebook NN is
unreliable on real captures.

### What changed vs run 1 (phone-on-phone)

- **Pose: 100% (was 75%).** Real monitor's larger marker pixels and lower
  subpixel pitch make ArUco detection trivially robust.
- **Inner decode: still 0%.** Even with cleaner display + camera capture,
  the continuous-coefficient catastrophe-germ codebook NN cannot classify
  256 codewords from real-world captures.

### What this confirms

This is **direct empirical confirmation of ADDENDUM_04's prior-art prediction.**
The screen-camera channel destroys subtle continuous-grayscale modulation
regardless of which screen is used. Better displays improve pose, but the
inner decode failure is at the substrate level, not the capture-pathway level.

`debug_manifest_zoom_run4_01.png` shows the canonical germ field side-by-side
with the rectified capture: visibly better than phone-on-phone (much less
high-frequency moiré), but the per-germ feature-to-noise ratio is still
insufficient for 256-way classification at amp=0.30.

### Files in run 4

- `results/debug_rectified_run4_01.png` — rectified frame for capture 1
- `results/debug_manifest_zoom_run4_01.png` — side-by-side canonical vs rectified
- `results/spike8b_results_run4_asus_correct_display.json` — per-capture results

## Conclusion across all 4 runs

| Run | Display | Pose | Inner decode | Diagnosis |
|---|---|---|---|---|
| 1 | phone screen | 6/8 | 0/6 | screen-camera moiré |
| 2 | Asus, broken file | 0/9 | n/a | display setup |
| 3 | Asus, broken file | 0/3 | n/a | display setup |
| 4 | Asus, fixed file + F11 | 3/3 | 0/3 | substrate-level channel mismatch |

**P3.A's pose layer (ArUco) works in real-world capture.**
**P3.A's inner substrate (continuous catastrophe-germ codebook) does not.**
The failure is exactly the one ADDENDUM_04 predicted from prior art: subtle
continuous-grayscale modulation at amp=0.30 is the regime the screen-camera
channel destroys.

The path forward is not more captures. It's **spike-9A** (per ADDENDUM_04 §5):
synthetic moiré-distortion harness as a closed-loop test bed, then evaluate
substrate variants (discrete classifier, increased amp, mid-band DCT, bandpass
decode) against it before committing to any of them.

