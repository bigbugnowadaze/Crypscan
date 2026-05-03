# Addendum 01 — `img2phox` integration (post-Phase-0 correction)

**Status:** Phase 0 follow-up. PR #1 (the original twelve deliverables) was merged on 2026-05-03 before the user updated the CRYPSOID repo with the missing `tools/img2phox/` directory and posted the AXP6 sample carrier as a GitHub Release asset on this repo. This addendum reflects what the original Phase 0 package would have said had `img2phox/` been present at authoring time.
**Scope:** corrections + extensions to the original proposal. Original docs not edited; this addendum is the delta.
**Reads:** `06_DECODER_RESEARCH_PLAN.md` and `07_INTEGRATION_BRIDGES.md` are the docs most affected. `refs/crypsoid/INDEX.md` is being updated alongside this addendum to point at `img2phox/`.

---

## 1. What changed since Phase 0 was authored

Two material updates from the user, both arriving after PR #1 merged:

1. **CRYPSOID repo now contains `tools/img2phox/`** — 26 Python files, 5,872 lines. Authoritative spec at `docs/img2phox_spec.md` (185 lines). This is the directory the user originally asked the agent to read; it did not exist in the clone Phase 0 was authored against. The original `refs/crypsoid/INDEX.md` note that "The closest equivalents are `tools/crypsorender/` and `tools/phoxbench/`" was correct at time of writing and is now stale.
2. **`sample-2.mp4.axp6.png` is published as a GitHub Release asset** at `https://github.com/bigbugnowadaze/Crypscan/releases/tag/png` (release name `sample-2.mp4.axp6.png`, tag `png`, 36,203,687 bytes). Verified for Phase 1: PNG signature OK, 11032×13120 pixels, bit_depth 2, color_type 3 (matches `aurexis_decode.py` line 84 and `05_INFORMATION_DENSITY_ANALYSIS.md` §1). Available at `https://github.com/bigbugnowadaze/Crypscan/releases/download/png/sample-2.mp4.axp6.png`.

The original Phase 0 package did not depend on either being present (the architecture digest sourced from `aurexis_decode.py`, the decoder plan made no claim about specific CRYPSOID inversion code existing). So the architectural argument is unchanged. But the engineering plan for Phase 1 — specifically the decoder research plan in `06` and the bridge structure in `07` — looks materially different now that `img2phox/` is on the table as a substrate to compose with.

## 2. What `img2phox/` actually is

From the spec doc (`docs/img2phox_spec.md` lines 1–7):

> **Status:** spec drafted + scaffolding + synthetic round-trip working, 2026-05-02.
> **Goal:** turn a folder of photos of a scene into a `.3dphox` file the existing CRYPSOID renderer can load.
> **Depends on:** existing `.3dphox` writer (v25 → v40), CRYPSOID renderer (Bar 2). No deps on lit-stack — image→phox is pure geometry.

It is the **producer-side** of CRYPSOID's pipeline: photos in, `.3dphox` scene out. CRYPSOID had previously been "consumer-side only" — accept gsplat's output PLY, compress it. `img2phox/` closes that loop.

### 2.1 Pipeline stages (from `docs/img2phox_spec.md` §"Architecture (5 stages)")

```
photos/                                            (input: directory of images)
   |
   v   F.1 load_photos.py
PhotoSet { images[], exif[] }
   |
   v   F.2 sfm.py       (Structure-from-Motion)
CameraBundle { intrinsics, extrinsics[N] }   +   PointCloud (sparse, ~1k pts)
   |
   v   F.3 mvs.py       (deferred to F.5; uses sparse cloud directly for now)
PointCloud (denser, ~100k pts)
   |
   v   F.3 optimize.py  (CPU blob optimizer)
BlobBundle { xyz, scales, quats, opacity, sh_dc, sh_rest }
   |
   v   F.4 encode.py
scene.3dphox  (v25 → v28-archive → optionally v31/v40)
```

### 2.2 What's actually in the source tree

| File | Lines | What it does |
|---|---:|---|
| `__init__.py` | 18 | Package metadata; exports the data classes |
| `data_classes.py` | 112 | `Photo`, `PhotoSet`, `CameraIntrinsics`, `CameraExtrinsics`, `CameraBundle`, `PointCloud`, `BlobBundle` — clean inter-stage contracts |
| `cli.py` | 112 | F.4 synthetic-roundtrip CLI; the original spec demo |
| `cli_real.py` | 145 | F.9 real-photo end-to-end demo (drives the pipeline with synthetic-rendered "real" photos for testing) |
| `cli_v10.py` | 244 | F.10 polished real-photo pipeline: ORB SfM + sparse-Jacobian BA + SGBM dense MVS + EXIF intrinsics + JIT optimizer + density schedule |
| `cli_phoxel.py` | 184 | F.12 Phoxel pipeline: CPU-only Plenoxel-class voxel grid → extract phoxoidal blobs |
| `load_photos.py` | 56 | PIL-based photoset loader |
| `preprocess.py` | 184 | EXIF intrinsics extraction, Brown-Conrady distortion correction (camera-DB), exposure normalization |
| `camera_db.py` | 116 | Hard-coded camera intrinsics + distortion for known phone/DSLR models |
| `sfm.py` | 281 | Synthetic-mode SfM (Phase F.2) |
| `sfm_real.py` | 286 | Real-photo incremental SfM via ORB + RANSAC + sparse BA (Phase F.5+) |
| `sfm_global.py` | 705 | Global SfM via rotation + LUD translation averaging (Phase F.11) |
| `sfm_colmap.py` | 265 | Optional COLMAP integration |
| `run_sfm_chunked.py` | 273 | Chunked driver for large photosets |
| `mvs.py` | 194 | Dense MVS via SGBM stereo + voxel fusion (Phase F.6) |
| `synth_scene.py` | 147 | Synthetic textured-cube renderer for F.2/F.3 tests |
| `optimize.py` | 207 | `quick_seed_from_pointcloud()`, `photometric_refine()` |
| `optimize_dense.py` | 167 | Dense optimizer (Phase F.8) |
| `optimize_jit.py` | 188 | Numba JIT'd dense optimizer (Phase F.8+) |
| `density_control.py` | 223 | 3DGS-paper-style adaptive density schedule (split, prune, max_blobs) |
| `phoxel.py` | 566 | Plenoxel-class CPU voxel grid + Numba JIT forward/backward (Phase F.12) |
| `phoxel_hessian.py` | 248 | Hessian-based blob extraction from voxel grid |
| `phoxel_octree.py` | 572 | Two-level sparse octree variant for memory savings (Phase F.12.3) |
| `run_phoxel_chunk.py` | 117 | Chunked Phoxel runner |
| `run_phoxel_octree.py` | 138 | Octree Phoxel runner |
| `encode.py` | 124 | `BlobBundle → .3dphox v25` writer (zlib chunks: xyz_u24_fixed, scale_f16, quat_i16_norm4, dc_rgb_opacity_u8, tier_labels_u8, sh_rest_f32) |

This is real working infrastructure, not scaffolding. The spec lists F.0 through F.4 as done in-session ("done in this session"), and F.5+ items (real-photo SfM, MVS, distortion handling, dense optimizer at scale) are present in the source tree as cli_real.py, cli_v10.py, and cli_phoxel.py — meaning the project moved past the spec's claimed "done" point.

### 2.3 What `img2phox/` produces

From `encode.py` lines 67–124 and `optimize.py` lines 30–72: the output is a CRYPSOID v25 attribute-group `.3dphox` file with chunks for `xyz_u24_fixed`, `scale_f16`, `quat_i16_norm4`, `dc_rgb_opacity_u8`, `tier_labels_u8`, and `sh_rest_f32`. Critically:

- **All output blobs are tier=2 (Tier C, Gaussian fallback).** From `optimize.py` line 71: `tier=np.full(N, 2, dtype=np.uint8), # all C-tier (Gaussian) for now`.
- **No germ chunks are emitted by `img2phox/`.** The 5-coefficient Pearcey-class germs (κ₁, κ₂, χ, ω, ζ) live downstream — they are computed at *render time* by CRYPSOID's renderer (`tools/crypsorender/math/germ.py` `fit_synthetic_germs_5()`, lines 105–168), not at *image-input time* by `img2phox/`.
- **The format magic produced is `CRYPSOID25\0`** (`encode.py` line 31), not `CRYPSOID40\0`. The newer `v40_native_germ_chunks_spec.md` exists in `docs/` but `img2phox/`'s encoder does not emit v40-native germ chunks.

So `img2phox/` is **image → 3D scene → standard 3DGS-style blobs**. The germ math is *separately* applied by the CRYPSOID renderer when the resulting `.3dphox` is loaded.

## 3. How this changes the proposal

The original `06_DECODER_RESEARCH_PLAN.md` opened with this framing (§1):

> CRYPSOID's existing pipeline goes **scene → render** (forward direction). The decoder needs **rendered_image → scene_germs** (reverse direction). This is a non-trivial inverse problem, not a syntactic transform.

This is now **partially wrong**. CRYPSOID's existing pipeline goes both directions:
- **scene → render**: `crypsorender` (forward, intact in the original framing).
- **images → scene**: `img2phox` (reverse, NOT acknowledged in the original framing).

But the framing is also **partially right**: `img2phox` solves a *different* inverse problem than the carrier decoder needs. Specifically:

| Dimension | `img2phox` | Phoxoidal carrier decoder |
|---|---|---|
| **Inputs** | Multiple photos (N≥3 typically; F.10 driver expects ~10–30) of an unknown scene | One captured image of a *known* carrier whose encoder placed germs at known scene positions |
| **Output** | A 3D scene reconstruction (camera poses + BlobBundle) recovered from photometric consistency | A list of catastrophe-germ classifications (5-coef germs) recovered from structural detection |
| **Problem class** | Multi-view structure-from-motion + dense reconstruction + dense optimization | Single-image structural feature extraction + classification + manifest-cluster bootstrap |
| **Per-blob output** | xyz, scale (3-vec), quat, opacity, sh_dc — *all Tier C, no germs* | (κ₁, κ₂, χ, ω, ζ) per germ + persistence-confidence score |
| **Underdetermination** | Bootstrap pair selection, scale ambiguity, drift | Manifest-cluster orientation/scale recovery; redundancy-vote across germ copies |
| **Computational shape** | SfM (cubic in cameras) + MVS (per-pair stereo) + optimizer (linear in blobs) | Scale-space (linear in pixels) + persistent homology (super-linear, may need tiling) + per-germ Mumford-Shah + per-germ inverted fit |

These are different problems. `img2phox` cannot directly decode a phoxoidal carrier — it would treat the carrier image as one frame in a missing multi-view set and would not recover germ classifications even if it produced a sparse cloud. But it ships a *substantial subset* of the engineering infrastructure the carrier decoder needs.

## 4. What carries over from `img2phox/` to the carrier decoder

This is the addendum's most useful content for Phase 1 planning. Each item below is a working module in `img2phox/` that the proposed carrier decoder can re-use rather than build from scratch.

### 4.1 Image preprocessing — direct reuse

`img2phox/preprocess.py`:

- `preprocess_photoset(photoset, fov_deg_fallback, exposure_method, verbose)` — full preprocessing pipeline (lines 155–end).
- `normalize_exposure(photoset, method='mean_match')` — exposure normalization across photos (lines 88–end).
- EXIF intrinsics extraction with FOV fallback.
- Camera-DB-driven Brown-Conrady distortion correction (uses `camera_db.py`).

For the carrier decoder, "EXIF intrinsics + Brown-Conrady distortion correction" is precisely the kind of preprocessing the V2 capture protocol's Galaxy S23 Ultra captures need before structural detection runs. The decoder can pass each captured carrier image through `preprocess_photoset(PhotoSet([single_photo]), ...)` and inherit the existing intrinsics database. This is a real reduction in the carrier decoder's preprocessing budget.

### 4.2 `.3dphox` encoder — direct reuse for the carrier *encoder*

`img2phox/encode.py`'s `encode_blobbundle_to_3dphox()` (lines 67–124) writes a v25 attribute-group container that the existing CRYPSOID renderer can load. The proposed carrier encoder (proposal `03` layer 4 — scene assembly) needs to produce a `.3dphox` file the existing renderer can render. `encode.py`'s writer is the natural starting point.

What the carrier encoder needs to extend:
- Add a new chunk for germ coefficients (the proposed `germ_5coef_carrier` chunk per `03` §5; analogous to but distinct from CRYPSOID v40's `germ_5coef_f16`).
- Add a manifest-cluster identifier chunk (per `03` §7).
- Possibly a new format magic (proposed `CRYPSOID_3DPHOX_VCAR_PHOXOIDAL_CARRIER` per `03` §2 layer 4); alternatively, extend the v25 manifest format string.

These extensions are additive on top of `encode.py`'s working v25 writer, not a rewrite.

### 4.3 Density-controlled optimizer — partial reuse for *encoder-side germ placement*

`img2phox/density_control.py` (223 lines) ships a 3DGS-paper-style adaptive density schedule (`DensityScheduleConfig`, `DensityScheduleState`, `density_step()`). `img2phox/optimize_jit.py` (188 lines) provides the Numba JIT'd optimization loop that uses it.

The proposed carrier *encoder* (proposal `08_HONEST_TRADEOFFS.md` §2 — "the encoder is real engineering, not a transcription") needs to solve a constrained-placement-optimization problem: place germs to satisfy detectability + non-overlap + Tier C preservation + redundancy. The 3DGS density schedule is the wrong objective function (it optimizes photometric loss, not steganographic-decode confidence) but it ships the right *algorithmic shape* — iterative gradient descent with split/prune density control.

Adapting `density_control.py`'s schedule to the carrier encoder's objective is a smaller engineering chunk than implementing it from scratch.

### 4.4 Numba JIT infrastructure — direct reuse for decoder hot paths

The persistent-homology / Mumford-Shah / inverted-germ-fit pipelines proposed in `06` §3 are all CPU-only by design (per the no-GPU rule). `img2phox/` already imports Numba (`from numba import njit, prange` in `phoxel.py`) and uses it for forward + backward voxel-render passes. The decoder's hot loops (per-germ Newton fit, per-tile persistence computation, per-pixel Mumford-Shah residual) can adopt the same Numba pattern with minimal infrastructure setup.

### 4.5 SfM / MVS — *not* directly reusable, but informative

The carrier decoder is fundamentally single-view (one captured image of a known carrier). SfM and MVS are multi-view operations. They do not transfer directly.

**However**, `img2phox/`'s SfM stack (`sfm.py`, `sfm_real.py`, `sfm_global.py`, `sfm_colmap.py`, plus the chunked drivers) is *the* substantial body of code the project would have written for a multi-view carrier extension (proposal `09_OPEN_QUESTIONS.md` §7 on video-frame carriers; proposal `03_PHOXOIDAL_CARRIER_ARCHITECTURE.md` §8.3 on cross-modal extensions). If the partners ever decide to support video carriers or multi-photo capture, `img2phox/`'s SfM stack is the substrate. Phase 1 can defer that question; it does not need to inform the static-image decoder design.

### 4.6 Phoxel voxel grid — speculatively reusable for one specific decoder design choice

`img2phox/phoxel.py` and `phoxel_octree.py` ship a CPU-only Plenoxel-class voxel reconstruction. From the docstring in `phoxel.py` (lines 30–37):

> A novel breakout path: Plenoxels (Fridovich-Keil et al. CVPR 2022) achieved 100× speedup over NeRF by replacing the MLP with a direct voxel grid + spherical harmonics. Their reference impl is CUDA. Nobody (to our knowledge) has shipped a CPU-only Plenoxel-class reconstruction that produces splat-format output.

For the carrier decoder, this is *speculatively* relevant: an alternative decoder design could fit a 3D phoxel grid against the captured image, then extract germs from the grid's local curvature (analogous to `extract_blobs_from_grid()` at `phoxel.py` line 467). This trades single-image-with-prior structural detection for a small voxel-fitting problem. It is a different design choice than the scale-space + Mumford-Shah + germ-fit composition proposed in `06` §3.5; whether either is the right answer is a Phase 1 measurement question.

The addendum does not commit to this alternative — it just notes it as a now-existing option that the original `06` did not consider because the substrate wasn't visible.

## 5. Updated effort estimates for Phase 1

The original `06_DECODER_RESEARCH_PLAN.md` §4.6 estimated:

| Component | Original effort | Revised effort | Why |
|---|---:|---:|---|
| 3.1 scale-space detection (off-the-shelf) | 1 week | **1 week** | Unchanged; off-the-shelf is unchanged. |
| 3.4 inverted germ-fit (port from CRYPSOID) | 1–2 weeks | **1–2 weeks** | Unchanged; the germ math source is the same. |
| 3.3 Mumford-Shah localization (custom) | 2 weeks | **2 weeks** | Unchanged; no Mumford-Shah analog in img2phox. |
| 3.2 persistent homology (off-the-shelf, integration work) | 1 week | **1 week** | Unchanged. |
| Manifest cluster detection (new) | 2 weeks | **2 weeks** | Unchanged; no manifest-cluster analog in img2phox. |
| Symbol decoder + redundancy vote | 1 week | **1 week** | Unchanged. |
| Synthetic test harness (no captures) | 1 week | **0.5 week** | `img2phox/synth_scene.py` is a working synthetic-scene harness; adapt for carriers rather than build from scratch. |
| Integration + first synthetic roundtrip | 2 weeks | **1.5 weeks** | `img2phox/`'s data classes (`Photo`, `PhotoSet`, etc.) are the natural inputs; the encoder side already has `encode.py`. |
| Captured-image roundtrip (V2 protocol) | 4 weeks | **3 weeks** | `img2phox/preprocess.py` (EXIF intrinsics + camera-DB distortion + exposure normalize) is a 1-week chunk we don't need to write. |
| **Subtotal (most-likely)** | **~15 weeks** | **~13 weeks** | Saved ~2 weeks of preprocessing + encoding scaffolding. |
| **Subtotal (with risk multipliers)** | **~30-40 weeks** | **~26-36 weeks** | Risk multipliers unchanged; their basis is the unsolved research, not the scaffolding. |

The revised estimate is modestly smaller. The decoder is still the largest single research risk; `img2phox/` reduces the scaffolding cost but does not reduce the research cost.

## 6. Updated bridge plan (delta against `07_INTEGRATION_BRIDGES.md`)

Bridges that *change* their pass criterion or scope:

### 6.1 Branch P1.1 — `PhoxCar Format Lock Bridge V1`

**Original:** "A `.3dphox` extension is specified, locked, and CI-verified." 
**Revised:** Same, with the **explicit constraint that the format extension is additive on top of `img2phox/encode.py`'s v25 writer**, not a parallel rewrite. The reviewer should be able to point at one file in `img2phox/` and say "this is what the carrier encoder builds on."

### 6.2 Branch P2.1 — `Crypsorender PhoxCar Profile Bridge V1`

**Original:** "CRYPSOID's renderer renders the new format magic with no GPU dependencies."
**Revised:** Same. **Plus:** the new carrier format must round-trip through `img2phox/encode.py`'s writer + CRYPSOID's renderer + the proposed germ-extraction decoder. Three-way roundtrip, not just two.

### 6.3 Branch P3.13 — `Synthetic Forward Roundtrip Bridge V1`

**Original:** "Encoder → renderer → decoder reproduces input payload byte-exact under zero capture noise. SHA-256 verification gate."
**Revised:** Same, but **the synthetic test harness can re-use `img2phox/synth_scene.py`'s primitives** (cube + sphere + plane synthetic scene; orbit cameras; deterministic render). This drops the "build a synthetic test harness" subtask of `06` §4.6.

### 6.4 New Branch P3.X — `img2phox Substrate Composition Bridge V1`

**New bridge.** Pass criterion: the carrier encoder and decoder import only the documented public API of `img2phox/` (the data classes from `__init__.py` plus `preprocess`, `encode`, and `density_control`'s public functions). No internal-API coupling. This protects against `img2phox/` evolving and breaking the carrier substrate.

### 6.5 Updated branch totals

| Branch | Original bridges | Revised bridges |
|---|---:|---:|
| P1 — Format and scene assembly | 4 | 4 |
| P2 — Renderer integration | 3 | 3 |
| P3 — Decoder | 6 | **7** (added P3.X above) |
| P4 — Tolerance and capture | 4 | 4 |
| P5 — Integration and release | 4 | 4 |
| **Total** | **21** | **22** |

The total bridge count grew by one. The cumulative effort estimate (`07` §2 "indicative target ~12-15 months") is roughly unchanged — the new bridge is a discipline check, not a substantial new build, and it's offset by the smaller scaffolding load on existing bridges.

## 7. The PNG sample carrier — Phase 1 access confirmed

The sample carrier is now reachable at:

```
https://github.com/bigbugnowadaze/Crypscan/releases/download/png/sample-2.mp4.axp6.png
```

Verification ran during this addendum:
- File size: 36,203,687 bytes.
- PNG signature: OK.
- IHDR: width=11032, height=13120, bit_depth=2, color_type=3 — exactly matches `aurexis_decode.py` line 84 expectations and `05_INFORMATION_DENSITY_ANALYSIS.md` §1's stated dimensions.
- Total pixels: 144,739,840 (matches `05` §1's number to the unit).
- Raw module capacity: 289,479,680 bits ≈ 34.51 MiB / 36.18 MB depending on convention.

For Phase 1, the PNG is a non-blocking dependency: roundtrip benchmarking against a known-good carrier is part of validating that the proposed phoxoidal carrier does not regress AXP6's bit-exactness contract on AXP6-format inputs. The straightforward Phase 1 pattern: download via `curl` from the release URL above; cache locally; treat as a fixture in the test harness.

No commitment needed from this addendum on whether the proposed phoxoidal-carrier's encoder should be able to *re-encode* this video payload — that is a workflow-fit question, not a substrate-correctness question.

## 8. Honest framing for the reviewer

This addendum does not change the architectural argument or the diffeomorphism-invariance claim or the honest-tradeoffs accounting. It changes one specific paragraph of `06_DECODER_RESEARCH_PLAN.md` (the framing in §1 that overstated CRYPSOID's pipeline as scene→render only) and modestly rescopes some Phase 1 effort estimates. The decision framework in `10_RECOMMENDED_DECISION_FRAMEWORK.md` is unchanged in substance.

The substantive update for the partners' joint review:

- **CRYPSOID has more inverse-direction infrastructure than the original Phase 0 documented.** Specifically, image preprocessing, `.3dphox` encoding, and density-controlled blob optimization are working substrates we can compose with rather than build from scratch.
- **The carrier decoder is still novel research.** `img2phox/` solves multi-view 3D scene reconstruction with standard 3DGS outputs; the carrier decoder solves single-view germ-classification from a known structured carrier. They are different problems even though they share scaffolding.
- **The bridge plan grows by one bridge** (a substrate-composition discipline check) and modestly shrinks per-bridge effort estimates.
- **Net effect on the decision framework:** none. The same three load-bearing questions (workflow scope / engineering budget / architectural willingness) drive the same Adopt / Redirect / Reject / Counter-propose recommendation.

The original Phase 0 package's `refs/crypsoid/INDEX.md` had a note explaining the absence of `tools/img2phox/`; that note was correct at time of writing and is now stale. The accompanying commit updates that file to point at `img2phox/` directly.

---

**Cross-references.** The original architecture is in `03_PHOXOIDAL_CARRIER_ARCHITECTURE.md`. The decoder research plan being amended here is in `06_DECODER_RESEARCH_PLAN.md`. The bridge plan being amended here is in `07_INTEGRATION_BRIDGES.md`. The decision framework, unchanged in substance, is in `10_RECOMMENDED_DECISION_FRAMEWORK.md`.
