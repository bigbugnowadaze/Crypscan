# Spike-8B capture protocol

**For:** Bug + Vince. ~2 hours, can be split across sessions.
**Goal:** characterize the real-world envelope of P3.A (ArUco fiducials + spike-7 substrate)
across phone × screen × distance × angle × lighting variations.
**Output:** ~50-80 captures that the harness will decode and report on.

The whole point: synthetic warps in P3.A and P3.B told us what the algorithm
*should* survive. This protocol tells us what the algorithm *actually* survives
when a real phone camera looks at a real screen. Discrepancies are the most
informative datapoint of the entire Phase 1.

---

## Equipment

**Phones (any subset is fine — more is better):**
- Samsung Galaxy S21 FE
- Samsung Galaxy Z Flip 4
- Samsung Galaxy S23 Ultra

**Screens:**
- MSI G27C4X (curved gaming monitor)
- Asus laptop screen (glossy or matte, note which)

**Source PNG:** `phoxcar/spike8b/reference_carrier.png` (1280×1280, 8-bit grayscale).

---

## Display setup (do once per screen)

1. Open `reference_carrier.png` full-screen in any image viewer (or in a browser
   with a black background — `<img src="reference_carrier.png">` on a body with
   `background:black; margin:0; display:flex; align-items:center; justify-content:center;`).
2. Set the screen to **maximum brightness**.
3. Disable any auto-adjustment / night-light / blue-light filter.
4. The carrier should fill at least 50% of the screen height.
5. Note the screen's reported resolution (e.g., "1920×1080 native") in your notes.

---

## Capture matrix

For **each (phone, screen) combination**, take **at least these captures**:

| # | Distance | Angle | Lighting | Notes |
|---|---|---|---|---|
| 1 | "comfortable read" (~30-50 cm) | head-on | bright (room lights on) | the easy baseline |
| 2 | "comfortable read" | head-on | dim (room lights off, screen-only) | photometric envelope test |
| 3 | "comfortable read" | head-on | mixed (window backlight) | natural-light realism |
| 4 | close (<20 cm — fills most of frame) | head-on | bright | minimum-distance test |
| 5 | far (carrier fills ~25% of frame) | head-on | bright | maximum-distance test |
| 6 | comfortable | tilted ~15° (rotate phone around vertical) | bright | small perspective tilt |
| 7 | comfortable | tilted ~30° | bright | larger perspective tilt |
| 8 | comfortable | rotated 90° (phone in landscape vs screen in portrait) | bright | rotation tolerance |
| 9 | comfortable | head-on | bright | one HANDHELD shot (slight motion blur expected) |

That's 9 captures × phones × screens. With 3 phones × 2 screens, that's **54 captures**.
Add a few "what if" shots if you want (sunlight glare on screen, phone behind glass, etc.).

**Time budget:** ~2 minutes per capture × 54 = ~2 hours. Take a break between phones.

---

## File naming convention

Save each capture as a JPEG (the phone's native format is fine). Use the file naming
convention so the analysis script can parse metadata:

```
{phone}_{screen}_{distance}_{angle}_{lighting}_{seq}.jpg
```

Where:
- `phone` ∈ {`s21fe`, `flip4`, `s23ultra`}
- `screen` ∈ {`msi`, `asus`}
- `distance` ∈ {`close`, `comfy`, `far`}
- `angle` ∈ {`headon`, `tilt15`, `tilt30`, `rot90`, `handheld`}
- `lighting` ∈ {`bright`, `dim`, `mixed`}
- `seq` is a 2-digit zero-padded sequence (`01`, `02`, ...) so re-takes don't overwrite.

Examples:
```
s21fe_msi_comfy_headon_bright_01.jpg
s21fe_msi_comfy_headon_dim_01.jpg
s23ultra_asus_close_headon_bright_01.jpg
flip4_msi_comfy_tilt30_bright_01.jpg
```

If you forget — fine, the script can also accept loose filenames; it just won't be
able to break the report down by axis. Just don't overwrite captures.

---

## Drop captures into the harness

1. Drop all the JPEGs into `phoxcar/spike8b/captures/raw/`. (This directory is
   gitignored — the photos themselves don't get committed; only the analysis report.)
2. From the `phoxcar/spike8b/` directory:
   ```
   python3 analyze.py
   ```
   This decodes each capture with the P3.A pipeline and writes per-capture results
   to `results/spike8b_results.json`.
3. Generate the human-readable report:
   ```
   python3 report.py
   ```
   Produces `results/SPIKE8B_REPORT.md` with pass/fail by axis.

If a capture decodes successfully, you'll see the literal text:
> "SPIKE-8B real-camera validation reference carrier..."

That's the win condition.

---

## What the harness reports

For each capture:
- **pose_ok**: did ArUco find all 4 markers?
- **sha256_ok**: did the decoded payload match the expected SHA-256?
- **transform**: the (a, b, γ) intensity-transform fit from pilots — characterizes
  display + camera photometric drift in the wild.
- **rs_corrected_frames**: how many RS frames the decoder had to repair.
- **decode_error**: if it failed, where (pose / pilots / manifest / payload).

Aggregated by phone × screen × condition, the report tells us:
- Which conditions are real-world-trivial (decode just works).
- Which conditions are real-world-fragile (P3.A's synthetic envelope didn't predict).
- What the actual photometric drift looks like across phone/screen pairs.
- Whether rolling-shutter shows up at all (S23 Ultra has a fast shutter; S21 FE less so).

---

## Edge cases / troubleshooting

- **Decoder always fails at "weak corners (NCC < ...)" / "missing markers"** — try
  cropping the photo to just the carrier region in your phone's photo app first.
  Then drop the cropped version into `captures/raw/` with the same naming convention.
  (The harness will get a `crop` step in v2 if this turns out to be common.)
- **Phone shoots in HEIC instead of JPEG** — convert to JPEG first (most phones have
  a setting for "Maximum compatibility" / "JPEG"). The harness reads JPEG/PNG only.
- **Screen has visible moiré in the photo** — that's expected at certain
  distance × resolution combinations. Take the photo anyway; it's a real-world
  artifact and a useful datapoint.
- **All captures from one phone fail** — record the phone + photo size in the report;
  we may need a phone-specific pre-processing step (resolution downsampling, EXIF
  orientation, colorspace conversion).

---

## After capture session

Push the analysis report (`results/SPIKE8B_REPORT.md` and `results/spike8b_results.json`)
to the branch. Keep the raw captures locally — don't commit them. We'll use the report
to scope P3.C (or to declare the production envelope is fine and pass on P3.C).
