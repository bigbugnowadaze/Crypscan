# phoxcar/spike8a — sidecar removal + fiducial pose recovery

**Status:** complete; result is **mixed and honest**
**Authorized:** 2026-05-04 (Bug, after auditing ChatGPT's response to spike-7)
**Goal:** validate that the substrate can decode without a JSON sidecar, recovering pose from the captured image alone via finder corners + manifest cluster.

## What spike-8A is

ChatGPT's spike-8A scope: synthetic-only geometric noise (no real captures), no JSON sidecar in the decode pipeline, format spec drives layout. The freeze in `../PHOXCAR_CAPTURE_SUBSTRATE_V0.md` locks layers 1-4 + 6-8; spike-8A is the layer-5 (pose recovery) experiment.

## Architecture

```
encode:
  fixed 1280x1280 canvas (format-spec)
  4 corner finders at canonical positions (FINDER_MARGIN=36 from edge)
    NW/NE/SW use FINDER_GLYPH_A=143 (38.7% bright at amp=1.0)
    SE uses FINDER_GLYPH_B=13 (asymmetric marker)
  manifest cluster (8 germs at first 8 grid slots)
    encodes "PHX1" magic + RS-encoded byte count (uint32 LE)
  4 calibration pilots at next 4 grid slots
  payload germs at remaining grid slots (raster order)
  spike-3 sigmoid render + 8-bit grayscale PNG

decode (NO SIDECAR):
  PNG -> read 8-bit grayscale
  blob detection (adaptive percentile threshold, no smoothing)
    -> 4 corner candidates (filtered by area in [100, 600])
  corner identification (rotation-tolerant via SE template-match anchor)
    -> homography (observed -> canonical 1280x1280)
    -> rectify
  read manifest at canonical positions -> RS byte count
  read pilots at canonical positions -> intensity transform fit
  inverse-correct rectified image
  read payload at canonical positions -> codebook NN -> bytes
  RS + AXP6 + Brotli + SHA-256 verify
```

## Headline result

| Test | Outcome |
|---|---|
| Zero-warp gate (sanity) | **PASS** — sidecar removal works |
| Small geometric noise | **PASS** for translation ≤ 20 px, scale [0.7, 1.0], shear ≤ 2°, rotation 0°/90° |
| Larger geometric noise | **FAIL** for tilt > 0°, rotation ∈ (0°, 90°), scale > 1.0 |
| Photometric noise | Narrower envelope than spike-7 — finder detection breaks before pilots can correct |

**The architectural concept (sidecar-free decode via fiducial pose recovery) is empirically demonstrated.** The simple corner-finder implementation has limited operating range — Phase 1 P3 needs proper fiducial detection (AprilTag, ArUco, or TopoTag-style topological finders).

## What works

```
Geometric:   translation_x  pass=[0, 5, 20]      fail=[50, 100]
Geometric:   rotation        pass=[0, 90]        fail=[5, 15, 45, 180]
Geometric:   scale           pass=[0.7, 1.0]     fail=[0.85, 1.18, 1.4]
Geometric:   shear           pass=[0, 2]          fail=[5, 10]
Geometric:   tilt_x/tilt_y   pass=[0]             fail=[5, 10, 20, 30]
Photometric: gaussian_intensity pass=[0.001, 0.005, 0.01]  (spike-7 had ≤ 0.10)
Photometric: jpeg            pass=[15, 50, 75, 90, 95]      (spike-7 had ≥ 15)
Photometric: brightness      pass=[±0.02]                    (spike-7 had ±0.10)
Photometric: contrast        pass=[0.85, 1.0, 1.18]          (spike-7 had ±0.40)
```

## What this surfaces (Phase 1 P3 implications)

### 1. The chicken-and-egg between finders and pilots

Spike-7's calibration pilots require the carrier to be RECTIFIED first (so positions are known). Spike-8A's finders need to be DETECTED on the un-rectified image (so we can rectify). When photometric drift shifts the finder bright regions below the adaptive threshold, finders fail BEFORE pilots can run.

Mitigations (Phase 1 P3):
- **Iterative pipeline**: detect → rectify → fit pilots → inverse-correct → re-detect → re-rectify (handles small drift).
- **Photometric pre-processing**: histogram normalization or local-contrast normalization before finder detection (fully bypasses calibration drift for the finder-detection layer).
- **Robust finder design**: finders that survive arbitrary photometric drift (e.g., AprilTag-style high-contrast black/white squares with quiet-zone borders).

### 2. The finders deform under perspective and rotation

Phoxoidal germs rendered at high amp (1.0) saturate to nearly-uniform bright disks. Under perspective tilt, the bright region deforms; the connected component changes shape and area; threshold + area-filter falls outside [100, 600].

Mitigations:
- **Multi-scale finder detection**: try multiple thresholds + area ranges, pick the candidate set that best forms a quadrilateral with known aspect ratio.
- **Phoxoidal AprilTag finders**: explicit topology (e.g., concentric phox-glyph rings with inner/outer asymmetry) that survives projective transforms.
- **Hough-circle or ellipse fitting**: detect finders as ellipses (perspective-distorted circles), use ellipse params for homography seed.

### 3. Spike-8A is a *proof of concept*, not a production pose-recovery system

The freeze doc (`PHOXCAR_CAPTURE_SUBSTRATE_V0.md`) is correct: spike-8A's job is to validate that **the architecture supports sidecar-free decoding**. It does. The simple finder implementation is sufficient for the smoke test (zero warp + tiny photometric noise). It is NOT sufficient for V2-protocol captures.

Phase 1 P3 must invest in proper fiducial design. Adapting an existing mature solution (AprilTag, ArUco) is the pragmatic path. A phoxoidal-thesis-aligned alternative (TopoTag-style) is the principled path. Both are real CV engineering — multiple weeks each, not a spike.

## What spike-8A is NOT

- ❌ A real-camera roundtrip — that's spike-8B (deferred until 8A's finder design hardens).
- ❌ A V2-protocol-ready substrate — needs the 8A→production fiducial upgrade.
- ❌ A regression of spike-7 — the photometric envelope narrows ONLY in spike-8A's specific finder-detection-first ordering. Spike-7's photometric envelope still applies for non-warped (sidecar-known) workflows.

## Files

| File | Purpose |
|---|---|
| `header.py`, `basis.py`, `density.py`, `solver.py`, `germ_codec.py`, `ecc.py`, `codebook.py`, `pilots.py`, `noise.py` | reused verbatim from spike-7 |
| `finders.py` | NEW — 4 corner finders, FINDER_GLYPH_A x3 + FINDER_GLYPH_B (SE) |
| `pose.py` | NEW — blob detect + corner ID + homography + rectification |
| `manifest.py` | NEW — 8-byte manifest cluster (PHX1 magic + RS byte count) |
| `encoder.py` | NEW — format-spec layout (1280x1280 canvas, no sidecar required) |
| `decoder.py` | NEW — sidecar-free decode pipeline |
| `geometric_noise.py` | NEW — translation/rotation/scale/tilt/shear sweeps |
| `test_tolerance_profile.py` | full geometric + photometric sweep |

## Reproduce

```bash
pip install brotli reedsolo numpy scipy Pillow scikit-image
cd phoxcar/spike8a
python3 test_tolerance_profile.py
```
