# Spike-8B capture protocol

**Goal:** characterize the real-world envelope of P3.A (ArUco fiducials + spike-7 substrate)
across phone × screen × distance × angle × lighting variations.

The whole point: synthetic warps in P3.A and P3.B told us what the algorithm
*should* survive. This protocol tells us what the algorithm *actually* survives
when a real phone camera looks at a real screen. Discrepancies are the most
informative datapoint of the entire Phase 1.

---

## ☆ Solo quick pass (start here)

**~9 captures, one phone, one screen, ~30-45 minutes.** Designed so a single
person can de-risk the whole experiment before committing to a full session.

If these 9 captures pass: the substrate handles real-world capture conditions
well enough that the full multi-phone × multi-screen matrix is probably
unnecessary. If they fail in concentrated ways: the failure pattern tells us
what to look for in a follow-up session (and saves Vince a wasted afternoon).

### Solo equipment

- **One phone** (Bug's S21 FE is the suggested starting choice).
- **One screen** (whatever's available — MSI G27C4X if convenient,
  laptop or any decent monitor otherwise).
- The reference carrier: `phoxcar/spike8b/reference_carrier.png`.

### Solo capture matrix (9 shots)

For the **single phone × single screen** combination, take these:

| # | Distance | Angle | Lighting | Filename suffix |
|---|---|---|---|---|
| 1 | comfortable (~30-50 cm) | head-on | bright (room lights on) | `comfy_headon_bright_01` |
| 2 | comfortable | head-on | dim (room lights off) | `comfy_headon_dim_01` |
| 3 | comfortable | head-on | mixed (window backlight) | `comfy_headon_mixed_01` |
| 4 | close (<20 cm — fills most of frame) | head-on | bright | `close_headon_bright_01` |
| 5 | far (carrier ~25% of frame) | head-on | bright | `far_headon_bright_01` |
| 6 | comfortable | tilted ~15° (rotate phone around vertical axis) | bright | `comfy_tilt15_bright_01` |
| 7 | comfortable | tilted ~30° | bright | `comfy_tilt30_bright_01` |
| 8 | comfortable | rotated 90° (phone in landscape vs screen in portrait) | bright | `comfy_rot90_bright_01` |
| 9 | comfortable | head-on | bright (HANDHELD — slight motion ok) | `comfy_handheld_bright_01` |

Filename format: `{phone}_{screen}_{suffix}.jpg` — e.g.
`s21fe_msi_comfy_headon_bright_01.jpg`. If you forget the convention,
the harness falls back to a generic bucket; just don't overwrite captures.

### Solo workflow

1. Display `reference_carrier.png` full-screen on your chosen screen
   (set max brightness, disable night-light/blue-light filters).
2. Take the 9 captures above with the S21 FE.
3. Drop them into `phoxcar/spike8b/captures/raw/`.
4. From the `phoxcar/spike8b/` directory, run:
   ```
   python3 analyze.py
   python3 report.py
   ```
5. Read `results/SPIKE8B_REPORT.md`. Commit it to the branch and tell Claude.

### Solo decision tree (what the result means)

- **9/9 PASS** → real-world envelope is fine. Vince's session probably
  unnecessary. P3.C is a research luxury, not a blocker. V1 ships on P3.A.
- **7-8/9 PASS** with concentrated failure (e.g. only `tilt30` fails) →
  one specific axis to investigate; targeted follow-up captures beat a
  full matrix. Maybe one more solo session before involving Vince.
- **4-6/9 PASS** → real-world is meaningfully harder than synthetic.
  Worth a full multi-phone × multi-screen session to characterize.
- **<4/9 PASS** → P3.A has a real-world brittleness we didn't predict.
  Investigate before any further captures; we may need to fix something
  in the encoder/decoder before more data helps.

---

## Full matrix (only if the solo pass surfaces something)

The full session — multiple phones × multiple screens × the same 9 conditions —
takes ~2 hours and is only worth doing if the solo pass tells us we need
broader coverage. Don't pre-commit to this; let the solo data decide.

## Equipment (full matrix)

**Phones:** Samsung Galaxy S21 FE, Z Flip 4, S23 Ultra.
**Screens:** MSI G27C4X (curved gaming monitor), Asus laptop screen.
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

## Full capture matrix

For **each (phone, screen) combination**, take the same 9 conditions as the
solo pass above. With 3 phones × 2 screens, that's **54 captures**. Add a few
"what if" shots if you want (sunlight glare on screen, phone behind glass, etc.).

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
