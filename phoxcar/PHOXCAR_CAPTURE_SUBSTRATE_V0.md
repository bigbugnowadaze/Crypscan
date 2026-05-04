# PHOXCAR Capture Substrate V0 — Frozen

**Status:** **FROZEN** as of 2026-05-04, after spike-7 PASS
**Authorization:** Bug + ChatGPT prior-art audit + spike-3-7 empirical validation
**Purpose:** lock the photometric substrate stack so spike-8 (geometric pose recovery) does not re-litigate symbol encoding, calibration pilots, ECC, codebook design, or visible carrier model. Spike-8 only attacks geometry.

This document is a freeze, not a release. Production substrate work continues per `phoxoidal_carrier_proposal/07_INTEGRATION_BRIDGES.md`. The freeze means: any spike-8+ change to layers 1-4 or 6-8 must come with explicit justification, not just "while I'm in here." Layer 5 is the open layer.

---

## Stack — frozen layers in **bold**

| # | Layer | Status | Source | Notes |
|---|---|---|---|---|
| 1 | Payload integrity | **FROZEN** | spike-3 (verbatim AXP6 inner header) | Brotli q=11 + 48-byte AXP6 header + SHA-256 — bit-exact AXP6 contract preserved |
| 2 | Channel coding | **FROZEN** | spike-3 / spike-6 ecc.py | Reed-Solomon RS(255, 223). 14% overhead. Corrects up to 16 byte-flips per 255-byte frame. |
| 3 | Symbol channel | **FROZEN** | spike-6 | 256-glyph phoxoidal codebook in c_ortho space, designed via farthest-point sampling (min pairwise distance 4.32). Decode via nearest-neighbor in Euclidean c_ortho metric. 8 bits / germ. |
| 4 | Calibration | **FROZEN** | spike-7 | 4 anchor pilots at known scene positions, intensity transform `I_observed = a + b · I_true^γ` fit via curve_fit, inverse-corrected pixel-wise before symbol decode. |
| 5 | Pose recovery | **OPEN** | spike-8 (in progress) | Replace JSON sidecar with TopoTag-style structural manifest cluster + fiducial pose recovery from captured image. |
| 6 | Carrier display | **FROZEN** | spike-3 | Sigmoid forward model `intensity = sigmoid(baseline + amp · H(s,t))` with `amp = 0.30, baseline = 0.0, sigma = 4.0 px, half_size = 12 px`. Sign-preserving, bounded in (0.01, 0.99), CRYPSOID-thesis-aligned. |
| 7 | Coefficient basis | **FROZEN** | spike-2 / spike-3 | Cholesky-orthonormalized 5-coefficient Pearcey-class catastrophe-germ basis (κ₁, κ₂, χ, ω, ζ from `tools/crypsorender/math/germ.py`). Per-coefficient noise decoupled. |
| 8 | Transport | **FROZEN** | spike-3 | 8-bit grayscale PNG (PIL `mode='L'`). PNG zlib lossless. |

## Empirical envelope at the freeze (spike-7 measurement)

The substrate handles the following photometric perturbations **byte-exact** (SHA-256 verified):

| Noise type | In-bounds severity | Margin vs realistic phone-camera |
|---|---|---|
| Gaussian intensity (σ) | ≤ 0.10 | 5-20× |
| JPEG quality | Q ≥ 15 | 5-6× |
| Focus blur (kernel σ) | ≤ 1.5 px | 1.5-3× |
| Gamma drift (γ) | [0.7, 1.4] = ±0.4 | at edge |
| Brightness shift (Δ) | ≤ ±0.10 | 2× |
| Contrast scaling (k) | k ∈ [0.6, 1.4] = ±0.40 | 4× |
| Salt-pepper rate | ≤ 0.005 | 5× (typical) |

What still fails (Phase 1 P3+ work, **NOT** a layer-1-4 problem):
- **Geometric transformations** (translation, rotation, scale, perspective tilt, shear, rolling shutter) — require pose recovery (layer 5, spike-8).
- **Salt-pepper rate ≥ 0.01** — needs robust per-germ fit (M-estimator); not a frozen-layer change.
- **Focus blur σ ≥ 2.0 px** — substrate-scale assumption; tunable if needed.
- **Tier C aesthetic-field interference** — Phase 1 P2.6 work, orthogonal to layer 5.
- **Density at AXP6-scale** (6M germs, full sample carrier) — Phase 1 P3 scaling validation.

## What this freeze means for spike-8 onward

Spike-8 (in progress) **may not modify**:
- Codebook design, codebook size, codeword selection
- Calibration pilot pattern or transform model
- ECC parameters or layer placement
- Carrier display function (sigmoid vs strict H² vs anything else)
- Coefficient basis or quantization
- AXP6 inner header layout

Spike-8 **may add**:
- Manifest cluster glyph design
- Finder cluster design (corner markers)
- Detection pipeline (blob → identify → homography)
- Rectification step BEFORE the spike-7 decoder

If spike-8 surfaces a finding that requires changing a frozen layer, that is documented as a freeze break and discussed before action. Examples of such surfaces:
- "Manifest cluster requires codeword 0 to be reserved for finder use." → freeze break in layer 3.
- "Sigmoid display function gradient is too low at finder positions for blob detection." → freeze break in layer 6.

Either of these would be raised explicitly, not assumed.

## Spike sequence (validated path, in order)

1. **Spike-3** — sigmoid carrier substrate, 8-bit gate PASS.
2. **Spike-4** — tolerance baseline; substrate is zero-margin under noise.
3. **Spike-5** — R=3 + RS(255, 191); modest improvement only.
4. **Spike-6** — codebook modulation; massive tolerance win (~100× Gaussian).
5. **Spike-7** — calibration pilots; gamma/brightness/contrast envelopes opened.
6. **Spike-8** — manifest cluster + fiducial pose (← current).
7. **Spike-9+** — real V2/V3 captures; Tier C; density at scale.

## Not in scope of this freeze

- The PHOX-ANALOG (digital-file) substrate — that's spike-3 itself, kept as a parallel mode for digital-file workflows. Frozen in its own right but separately from this capture-mediated substrate.
- The CRYPSOID `.3dphox` format extension. Phase 1 P1 will add a new format magic; the spike-3-7 carriers used standalone PNG.
- Aurexis Core V3 lane bridge documents (`07_INTEGRATION_BRIDGES.md`). Those still need authoring per `phoxoidal_carrier_proposal/`.

## Cross-references

- `phoxoidal_carrier_proposal/03_PHOXOIDAL_CARRIER_ARCHITECTURE.md` — the architectural proposal layers. Spike-3-7 instantiate layers 1-3 + 5 + 9; spike-8 will instantiate layer 7 (manifest cluster).
- `phoxoidal_carrier_proposal/06_DECODER_RESEARCH_PLAN.md` — the original 6-9-month decoder research plan. Spike-3-7 collapse the bulk of §3 (no persistent homology, no Mumford-Shah, no nonlinear LM needed).
- `phoxoidal_carrier_proposal/07_INTEGRATION_BRIDGES.md` — Phase 1 bridge structure. Spike-8 corresponds roughly to Branch P3.12 (Manifest Cluster Detection Bridge V1).
- `phoxcar/spike3/results/SPIKE_REPORT.md` — initial substrate gate.
- `phoxcar/spike4/results/SPIKE4_REPORT.md` — tolerance baseline.
- `phoxcar/spike6/results/SPIKE6_REPORT.md` — codebook modulation result.
- `phoxcar/spike7/results/SPIKE7_REPORT.md` — calibration pilots result.
