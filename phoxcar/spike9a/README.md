# phoxcar/spike9a — synthetic channel + substrate variants

**Status:** complete; central hypothesis validated
**Authored:** 2026-05-04 (after spike-8B run 4 + ADDENDUM_04)
**Goal:** confirm or deny that P3.A's failure on real-world captures is
**channel-mismatch** (continuous-grayscale eaten by subpixel × Bayer +
JPEG), not insufficient ECC.

## What spike-9A is

A **closed-loop synthetic test bed** for substrate variants. Lets us
iterate on substrate design without needing more real-camera captures
each time.

```
encode payload with substrate variant V_i
  -> apply synthetic screen-camera channel (calibrated to spike-8B)
  -> decode with substrate variant V_i
  -> measure pass/fail + per-germ classifier confidence

if V_i passes synthetic channel where V0 fails:
  high-confidence prediction that V_i passes real hardware too
  -> earned the right to spike-9B (real-hardware re-test)

if V_i also fails synthetic channel:
  the design is fundamentally insufficient for this channel
  -> deeper substrate work needed (color channels, DCT, neural)
```

## Headline result

| Variant | Description | Channel result |
|---|---|---|
| V0 | P3.A as-is (256 cw, coefficient-space LSQ + NN) | FAILS exactly like spike-8B run 4 |
| V1 | 256 cw, image-space NCC (decoder change only) | partial — fails at AXP6 inner header |
| **V2** | **16 cw discrete, image-space NCC (full sub) ** | **manifest 4/4 ✓** |
| V3 | V2 + amp=0.6 | same — manifest 4/4 ✓ |

**Empirically: the discrete substrate clears synthetic channel where
P3.A doesn't.** ADDENDUM_04 §3 #1 recommendation validated.

See `results/SPIKE9A_REPORT.md` for full analysis.

## Run

```bash
pip install brotli reedsolo numpy scipy Pillow scikit-image opencv-python
cd phoxcar/spike9a
python3 test_channel_calibration.py     # verifies channel reproduces real failure
python3 test_substrate_variants.py       # V0..V3 comparison sweep
```

## Files

| File | Purpose |
|---|---|
| `header.py` ... `pose.py`, `encoder.py`, `decoder.py` | reused from p3a_aruco (frozen substrate) |
| `channel.py` | synthetic screen-camera distortion stack |
| `discrete_codebook.py` | N-codeword subset selection + NCC classifier |
| `discrete_decoder.py` | P3.A decoder with image-space NCC instead of coefficient LSQ |
| `test_channel_calibration.py` | verify channel reproduces spike-8B run 4 failure |
| `test_substrate_variants.py` | V0-V3 comparison sweep |
| `results/SPIKE9A_REPORT.md` | full analysis + recommendation |

## Recommended next step

**Spike-9B**: build a complete 16-nibble-pair codec (2 germs per byte
for full 8-bit byte recovery), regenerate the reference carrier, re-run
the spike-8B capture protocol on real Asus + S21 FE. ~1-2 days.
