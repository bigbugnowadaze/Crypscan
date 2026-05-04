# phoxcar/spike5 — R=3 redundancy + RS(255, 191)

**Status:** complete
**Authorized:** 2026-05-04 (Bug)
**Predecessors:** spike-3 (sigmoid carrier substrate), spike-4 (tolerance profile that revealed the brittleness)
**Goal:** test whether per-germ replication (R=3) + stronger ECC (RS(255, 191) → 12.5% byte tolerance vs spike-3's 6.3%) widens the photometric noise envelope. Same noise sweep as spike-4, like-for-like comparison.

## Pipeline (vs spike-3 / spike-4)

```
encode:
  payload bytes
    Brotli q=11 compress
    AXP6 inner header
    Reed-Solomon RS(255, 191)                      [stronger; spike-4 used (255, 223)]
    R-fold byte replication (R=3)                   [NEW]
    pad to 5-byte germ boundary
    bytes -> c_ortho -> theta_raw
    sigmoid render (spike-3, unchanged)
    8-bit grayscale PNG

decode:
  PNG -> linear LSQ fit per germ position
       -> 5 bytes per germ
       -> strip pad to recover R*N replicated stream
       -> per-byte majority vote across R copies     [NEW]
       -> RS(255, 191) decode (up to 32 errors/frame)
       -> AXP6 header parse -> Brotli decompress -> SHA-256 verify
```

## Files

| File | Origin |
|---|---|
| `header.py`, `basis.py`, `density.py`, `solver.py`, `germ_codec.py` | reused from spike-3 |
| `noise.py` | reused from spike-4 |
| `ecc.py` | NEW — RS(255, 191) instead of (255, 223) |
| `redundancy.py` | NEW — R-fold replicate + per-byte majority vote |
| `encoder.py`, `decoder.py` | NEW — composed pipeline with R |
| `test_tolerance_profile.py` | re-runs spike-4's exact sweep |
| `results/SPIKE5_REPORT.md` | results + spike-4 comparison |

## Reproduce

```bash
pip install brotli reedsolo numpy scipy Pillow
cd phoxcar/spike5
python3 test_tolerance_profile.py
```
