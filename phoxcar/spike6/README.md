# phoxcar/spike6 — codebook modulation (256 phoxoidal glyphs)

**Status:** complete; **massive tolerance win**
**Authorized:** 2026-05-04 (Bug, after auditing ChatGPT's analysis)
**Predecessors:** spike-3 (sigmoid carrier substrate), spike-4 (tolerance baseline), spike-5 (R=3 + RS — modest improvement)
**Goal:** test ChatGPT's most important architectural insight (point 5): replace continuous 5-coefficient analog encoding with a finite codebook of phoxoidal glyphs decoded by nearest-neighbor matching. Prior art: QR codes, AprilTag, ArUco, watermarking literature — every successful camera-decoded format uses categorical symbols, not analog parameter recovery.

## Pipeline

```
encode:
  payload bytes
    Brotli q=11 compress
    AXP6 inner header
    Reed-Solomon RS(255, 223)        (back to spike-3 baseline; standard RS suffices)
    each byte -> codebook[byte]      [NEW: 256-glyph codebook; 1 byte/germ]
        codebook is 256 maximally-separated points in c_ortho space
        (farthest-point sampling from a 20k-point pool)
    c_ortho -> theta_raw via M_to_raw
    sigmoid render (spike-3, unchanged)
    8-bit grayscale PNG

decode:
  PNG -> linear LSQ fit per germ (spike-3, unchanged)
       -> theta_raw -> c_ortho via M_to_ortho
       -> nearest-neighbor against 256-glyph codebook    [NEW]
       -> 1 byte per germ
       -> RS(255, 223) decode
       -> AXP6 + Brotli + SHA-256 verify
```

## Cost / benefit

- **5× density penalty.** 1 byte/germ vs spike-3's 5 bytes/germ. The price for digital-symbol robustness over analog precision.
- **~100× noise tolerance gain on Gaussian intensity** (σ = 0.001 → 0.10).
- **Universal JPEG tolerance** (Q ≥ 15 passes; spike-5 maxed at Q = 90).
- **Substantial focus-blur tolerance** (σ_blur ≤ 0.3 px → ≤ 1.5 px).
- **Calibration drift partially addressed** (brightness ±0.02, contrast ±18% now in-bounds).
- **Wall time** ~0.25 s/decode; well within the 30 s budget.

## Files

| File | Origin |
|---|---|
| `header.py`, `basis.py`, `density.py`, `solver.py`, `germ_codec.py`, `ecc.py` | reused from spike-3 verbatim |
| `noise.py` | reused from spike-4 verbatim |
| `codebook.py` | NEW — farthest-point-sampling codebook design |
| `encoder.py`, `decoder.py` | NEW — codebook-modulation pipeline |
| `test_tolerance_profile.py` | re-runs spike-4's exact sweep on the spike-6 substrate |
| `results/SPIKE6_REPORT.md` | results + spike-3-5-6 comparison |

## Reproduce

```bash
pip install brotli reedsolo numpy scipy Pillow
cd phoxcar/spike6
python3 test_tolerance_profile.py
```
