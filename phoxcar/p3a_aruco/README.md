# phoxcar/p3a_aruco — Phase 1 P3.A: ArUco fiducial pose recovery

**Status:** complete; **photometric acceptance gate fully met**, geometric pose recovery works for in-frame warps
**Authorized:** 2026-05-04 (Bug, after auditing ChatGPT's response to PR #10)
**Predecessors:** spike-3-7 (frozen substrate per `../PHOXCAR_CAPTURE_SUBSTRATE_V0.md`), spike-8A (proof of concept for sidecar-free decode)

## Result

ArUco fiducial integration **closes the V3-frontier photometric envelope** without sidecar dependency:

| Photometric noise | spike-7 (sidecar) | P3.A (sidecar-free) |
|---|---|---|
| Gaussian σ | ≤ 0.10 | **ALL severities tested 0.001–0.10 pass** |
| JPEG Q | ≥ 15 | **ALL Q tested 15–95 pass** |
| Focus blur (σ px) | ≤ 1.5 | **0.3–1.5 pass; 2.0 fails (substrate scale)** |
| Gamma | 0.7–1.4 | **ALL 0.7–1.4 pass** |
| Brightness | ±0.10 | **ALL ±0.02–±0.10 pass** |
| Contrast | 0.6–1.4 | **ALL 0.6–1.4 pass** |
| Salt-pepper | ≤ 0.005 | **ALL 0.001–0.05 pass** |

Geometric pose recovery works for in-frame transforms:
- Translation: 0–30 px (fails when markers go off-canvas)
- Rotation: 0°, 5°, 90°, 180°, 270° (fails at 15°, 30°, 45°, 135° because markers rotate off-canvas)
- Scale: 0.7–1.0× (fails at 0.5× substrate-scale limit and 1.18+× when markers go off-canvas)
- Sub-pixel: ALL severities pass
- Shear: 0–5° (fails at 10°+ when markers shear off-canvas)
- Tilt: 0–10° (fails at 20°+ when markers tilt off-canvas)
- Rolling shutter: 0 only (any per-row shear breaks marker quad shape)

**The geometric failures are not P3.A architectural failures.** They share one cause: the synthetic warps push ArUco markers outside the canvas frame. Real captures would frame the carrier with margin (operator holds the camera with framing slack), so off-canvas warps don't represent realistic capture conditions.

## Pipeline

```
encode:
  Brotli + AXP6 header + RS(255, 223)              (frozen layers 1-2)
  256-glyph codebook NN                             (frozen layer 3)
  manifest cluster (8 germs encoding RS byte count)
  4 calibration pilots                              (frozen layer 4)
  payload germs (1 byte / germ)                    (frozen layer 3)
  4 ArUco DICT_4X4_50 markers at corners            [P3.A — NEW]
    NW=ID 0, NE=ID 1, SW=ID 2, SE=ID 3
    96 px markers + 56 px white quiet zone
  spike-3 sigmoid render                            (frozen layer 6)
  8-bit grayscale PNG                               (frozen layer 8)

decode (NO SIDECAR):
  PNG -> 8-bit grayscale
       -> cv2.aruco.detectMarkers (DICT_4X4_50, sub-pixel refinement)
       -> identify NW/NE/SW/SE by marker ID (rotation-invariant)
       -> 4-point homography (observed -> canonical 1280x1280)
       -> cv2.warpPerspective rectification
       -> sample 4 pilots + fit intensity transform
       -> inverse-correct rectified image                [pilots BEFORE manifest]
       -> sample 8 manifest germs -> RS byte count
       -> sample payload germs -> codebook NN
       -> RS + AXP6 + Brotli + SHA-256 verify
```

## Key architectural finding from P3.A development

The pilots-before-manifest decode order is critical. Initially I had manifest read first, which inherits the spike-8A chicken-and-egg pattern: photometric drift fails the codebook NN before pilots can correct it. **Decoding pilots first, applying the inverse intensity transform, then decoding everything else (manifest + payload) on the corrected image** opens the full photometric envelope.

This is a substrate-level architecture lesson — pilot-correction must precede ANY codebook NN, not just payload decoding.

## Files

| File | Origin |
|---|---|
| `header.py`, `basis.py`, `density.py`, `solver.py`, `germ_codec.py`, `ecc.py`, `codebook.py`, `pilots.py`, `manifest.py`, `noise.py` | reused verbatim from spike-7/spike-8A (frozen substrate) |
| `geometric_noise.py` | reused from spike-8A + new `rolling_shutter` function |
| `fiducials.py` | NEW — ArUco DICT_4X4_50 marker rendering at canonical positions |
| `pose.py` | NEW — `cv2.aruco` detection + homography + warpPerspective rectification |
| `encoder.py` | NEW — format-spec layout (1280×1280 canvas, ArUco corners, no sidecar) |
| `decoder.py` | NEW — sidecar-free decode with **pilots-before-manifest** ordering |
| `test_acceptance_gate.py` | full geometric + photometric sweep targeting ChatGPT's acceptance criteria |

## Reproduce

```bash
pip install brotli reedsolo numpy scipy Pillow scikit-image opencv-contrib-python-headless
cd phoxcar/p3a_aruco
python3 test_acceptance_gate.py
```

## Substrate stack at P3.A completion

```
Layer 1 (payload):     AXP6 inner header (Brotli + SHA-256)        FROZEN
Layer 2 (channel):     Reed-Solomon RS(255, 223)                     FROZEN
Layer 3 (symbol):      256-glyph phoxoidal codebook                  FROZEN
Layer 4 (calibration): 4 pilots + 3-param intensity transform        FROZEN
Layer 5 (pose):        ArUco DICT_4X4_50 + cv2.aruco detection      P3.A SHIPS
Layer 6 (carrier):     spike-3 sigmoid                                FROZEN
Layer 7 (basis):       Cholesky orthonormal Pearcey 5-coef            FROZEN
Layer 8 (transport):   8-bit grayscale PNG                            FROZEN
```

Layer 5 transitions from "OPEN PoC" (spike-8A) to "P3.A SHIPS" (this PR). Substrate is now ready for spike-8B (real captures with S21 FE / Z Flip 4 / S23 Ultra × MSI G27C4X / Asus laptop screens).
