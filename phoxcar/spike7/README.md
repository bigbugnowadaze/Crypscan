# phoxcar/spike7 — calibration pilots

**Status:** complete; all predicted improvements achieved or exceeded
**Authorized:** 2026-05-04 (Bug, after auditing ChatGPT's response to spike-6)
**Predecessors:** spike-6 (codebook modulation — the architectural pivot)
**Goal:** address the spike-6 calibration-drift failures (gamma, brightness, contrast) by encoding known anchor codewords at known scene positions, fitting an intensity transform from anchor recovery, and inverse-correcting the captured image before decode.

## Pipeline (vs spike-6)

```
encode:
  Brotli + AXP6 header + RS(255, 223)              (unchanged)
  each byte -> codebook[byte]                      (unchanged)
  reserve N anchor positions in the grid           [NEW]
  place chosen anchor codewords at anchor positions [NEW]
  pack remaining payload germs into non-anchor positions
  sigmoid render + 8-bit grayscale PNG

decode:
  PNG -> read raw 8-bit grayscale
       -> at known anchor positions, gather (I_true, I_observed) sample pairs
       -> fit transform I_observed = a + b * I_true^gamma            [NEW]
       -> apply inverse transform pixel-wise to entire carrier        [NEW]
       -> spike-6 LSQ + nearest-neighbor decode (unchanged)
       -> RS + AXP6 + Brotli + SHA-256 verify
```

## Anchor design

4 anchor codewords selected from the 256-glyph codebook to span the
intensity dynamic range. Selection: greedy farthest-point sampling on
codeword *patch-mean intensity* (start with darkest + brightest, fill
in between). Placement: 4 corners of the grid layout (top-left,
top-right, bottom-left, bottom-right). Cost: 4 germs out of ~263 total
(1.5% overhead).

The 4 × 625 ≈ 2,500 anchor sample pixels give the curve_fit a
substantial SNR for the 3-parameter transform fit (a, b, γ).

## Files

| File | Origin |
|---|---|
| `header.py`, `basis.py`, `density.py`, `solver.py`, `germ_codec.py`, `ecc.py`, `codebook.py`, `noise.py` | reused verbatim from spike-6 (and spike-4 for noise) |
| `pilots.py` | NEW — anchor-codeword selection + transform fit + inverse |
| `encoder.py` / `decoder.py` | modified to reserve / read pilot positions |
| `test_tolerance_profile.py` | re-runs the spike-4 sweep on the spike-7 substrate |
| `results/SPIKE7_REPORT.md` | results + spike-6/7 comparison |

## Reproduce

```bash
pip install brotli reedsolo numpy scipy Pillow
cd phoxcar/spike7
python3 test_tolerance_profile.py
```
