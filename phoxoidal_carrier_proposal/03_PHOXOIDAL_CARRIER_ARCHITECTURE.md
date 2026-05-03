# 03 — Phoxoidal Carrier Architecture

> The proposed architecture in full. Builds on `01_AXP6_ARCHITECTURE_DIGEST.md` (what AXP6 actually is) and `02_FAILURE_MODEL_ANALYSIS.md` (why AXP6's substrate cannot defend the V2 frontier with more redundancy). Defers the math claim to `04_DIFFEOMORPHISM_INVARIANCE_ARGUMENT.md` and the honest costs to `08_HONEST_TRADEOFFS.md`.

---

## 1. The substrate move in one paragraph

Replace AXP6's pixel-grid carrier with a **phoxoidal field**: a 3D scene of catastrophe-germ blobs (CRYPSOID's 5-coefficient Pearcey-class basis) rendered to a 2D viewport for display. The "PNG" is one rendered viewport of the scene, not the format itself. The decoder is a **catastrophe-germ extractor** that recovers structure (not pixels) from a captured image. AXP6's payload-integrity contracts (Brotli + SHA-256 + bit-exact verification, plus an `AXP6`-equivalent magic + manifest) are preserved as outer wrappers around the new carrier; they were never the architectural problem.

## 2. The conceptual layer table

This is the table from the v4 handoff, expanded with implementation specifics tied to actual CRYPSOID and Aurexis Core source.

| # | Layer | What it is | Inherited from | Implementation specifics |
|---|---|---|---|---|
| 1 | **Payload** | Arbitrary file bytes | AXP6 verbatim | Same as `aurexis_decode.py` lines 535–548. Brotli compress, SHA-256 hash. |
| 2 | **Inner header** | `AXP6`-equivalent fixed-format prefix | AXP6 verbatim (with the magic and version possibly renamed — `09_OPEN_QUESTIONS.md` §3) | Same 48-byte fixed prefix: magic + version + comp_method + original_size + compressed_len + sha256 + filename_len + filename. |
| 3 | **Symbol encoding** | Compressed bytes → catastrophe-germ coefficient sequences | New | Each germ encodes `5 × N_bits` bits via its 5-coefficient basis (κ₁/κ₂ + Pearcey χ/ω + swallowtail ζ — `tools/crypsorender/math/germ.py` lines 23–30). For Phase 0 budget: 8 bits per coefficient → 40 bits per germ; see `05_INFORMATION_DENSITY_ANALYSIS.md` for the budget analysis and §6 below for the bit-allocation discussion. |
| 4 | **Scene assembly** | Germs placed in a 3D phoxoidal scene | CRYPSOID `.3dphox` v0.4 family (`docs/FORMAT.md` §"v0.4 (planned)") | Tier dispatch is structural (§3 below). The scene has a Tier C "aesthetic" Gaussian field plus Tier A/B catastrophe-germ blobs carrying payload. Extension to a new format magic — proposed: `CRYPSOID_3DPHOX_VCAR_PHOXOIDAL_CARRIER` — to be settled with Bug. |
| 5 | **Render** | 2D viewport rendering of the scene | CRYPSOID `crypsorender` (~1,600 LoC pure numpy, `docs/crypsorender_architecture.md`) | The PNG/image is a render output, not the format. Resolution-flexible. Must respect CRYPSOID's no-GPU rule (§9 below). |
| 6 | **Display** | The rendered image shown on a screen, printed, or embedded in a visual medium | New | The carrier can look like a photograph, brand pattern, ambient texture, etc., because germs are subliminal singularities, not visible markers. See §4 below. |
| 7 | **Capture** | Phone camera, scanner, or digital file read | Aurexis E/D pipeline; V2 capture protocol (`V2_CAPTURE_PROTOCOL.md`) | Capture introduces the smooth coordinate transformations enumerated in `02_FAILURE_MODEL_ANALYSIS.md` §2.1; structural decode is invariant to them by the argument in `04_DIFFEOMORPHISM_INVARIANCE_ARGUMENT.md`. |
| 8 | **Germ extraction** | Find and classify catastrophe singularities in the captured image | New | Toolbox: scale-space methods (Lindeberg), persistent homology (gudhi/ripser), Mumford-Shah singularity localization, plus CRYPSOID's existing germ-fitting code inverted. See `06_DECODER_RESEARCH_PLAN.md` for the full plan and risks. |
| 9 | **Symbol decoding** | Germ coefficient sequences → bytes | New | Inverse of layer 3. Validation via per-germ persistence scores + redundancy-vote (see §5 below for the redundancy structure). |
| 10 | **Payload verification** | Brotli decompress + size check + SHA-256 verify | AXP6 verbatim | Same as `aurexis_decode.py` lines 567–585. Bit-exact end-to-end contract preserved. |

The layers above the rendered image (1, 2, 10) carry over from AXP6 unchanged. The layers below the rendered image (3, 4, 5, 8, 9) are new but compose entirely from CRYPSOID's existing math and Aurexis Core's V2 capture substrate. The new substrate is not built from scratch; it is a composition of two largely-existing substrates with a thin new symbol-encoding layer.

## 3. Tier dispatch becomes structural, not positional

This is the conceptual move that makes the architectural transition coherent. AXP6's CORE/BODY/EDGE describe *where blocks live geometrically* (`aurexis_decode.py` lines 222–255). The phoxoidal carrier's tiers describe *what kind of structure each component encodes*:

| Tier | Role | Substrate | Visual character |
|---|---|---|---|
| **Tier C** (Gaussian smooth field) | Carrier aesthetic | CRYPSOID Tier C splats (anisotropic Gaussians, EWA-projected). Same math as `tools/crypsorender/math/ewa.py` and `pipeline/rasterize.py`. | The carrier *looks like* whatever the operator wants — a photograph, a brand pattern, an ambient texture. Carries no payload. |
| **Tier B** (germs with exact-residual correction) | Payload + bit-exact correction | CRYPSOID Tier B splats (5-coef germ + per-tier-group residual chunks, `docs/FORMAT.md` §"v28 EXACT archive"). Each germ is a payload-bearing structural element. | Subliminal singularities in the intensity field. Not visually salient as data, the way watermarks live in DCT space rather than pixel space. |
| **Tier A** (full germs) | Payload | CRYPSOID Tier A splats (5-coef germ + Newton solver, `tools/crypsorender/math/germ.py` lines 54–95). | Same subliminal character as Tier B; differ in whether they carry a per-germ correction. |

The tier-dispatch math is *the same as CRYPSOID already uses for 3D scene compression*. `tools/crypsorender/math/germ.py` is the load-bearing module: it defines the 5-coefficient germ basis (`germ_basis()` lines 23–30), the Newton solver for closest-point on the germ chart (`closest_point_on_germ()` lines 54–95), and the synthetic germ fitter (`fit_synthetic_germs_5()` lines 105–168). The proposal does not invent the germ math; it *re-uses* it for a different physical substrate.

The empirical case for the structural choice is `reports/TIER_1_results.md` (lines 11–14): **2.0× killer ratio across four real meshes (Happy Buddha, Armadillo, Doom combat, Audi A5) at every budget tested**. Phoxoidal blobs are demonstrably better than Gaussians at carrying *structural* information — which is exactly what we want them doing in the new carrier substrate.

## 4. What the carrier looks like

This is one of the new affordances that simply does not exist in AXP6.

An AXP6 carrier looks like 2-bit-indexed noise. There is no other option — every pixel is one of four palette indices, and the modulation pattern is dictated by the manifest layout, the tier assignment, the parity rows, and the integrity rows. AXP6 carriers are clearly *data*; that is part of their identity.

A phoxoidal carrier can look like *anything that is a valid render of a `.3dphox` scene*:

- **Photographic.** Tier C carries a rendered photographic field (a person, a product, a landscape). Tier A/B germs are subliminal singularities embedded in the intensity gradients of the photograph. The visible image is the photograph; the data is the structural perturbation in the gradients.
- **Brand asset.** Tier C carries a rendered brand pattern (logo, packaging, marketing imagery). Tier A/B germs ride along.
- **Ambient texture.** Tier C carries an ambient pattern (wallpaper, fabric, abstract art). Tier A/B germs hide inside.
- **Functional graphic.** Tier C is intentionally a UI element (a button, an icon, a poster). Tier A/B germs are the data.

The carrier becomes a **design surface**. This is a market-relevant difference that compounds the technical difference. It also creates new responsibilities (`08_HONEST_TRADEOFFS.md` §4): the operator must be honest about the presence of the data layer, and there is a set of trust-and-safety questions about steganographic carriers that look like benign content.

## 5. Inherited integrity contracts — what carries forward and how

AXP6's payload-level guarantees stay verbatim:

1. **Brotli compression** of the payload before symbol-encoding. Same algorithm, same library, same `comp_method == 1` semantics from `aurexis_decode.py` line 567.
2. **SHA-256 hash** of the original payload, stored as an outer manifest field, verified after decode against `hashlib.sha256(decompressed).digest()` (line 583).
3. **`AXP6`-equivalent magic + manifest** (probably renamed for clarity — see `09_OPEN_QUESTIONS.md` §3) declaring payload size, compression method, hash, encoding parameters. Same role as AXP6's manifest (`aurexis_decode.py` lines 272–330), different storage medium.

AXP6's *carrier-level* defenses (parity, interleaving, CRC) are replaced by structural equivalents that compose with the new substrate:

### 5.1 Redundant germs (parity-equivalent)

Each payload bit is encoded in N germs at distinct scene positions. N is configurable (Phase 1 must measure the right value); a reasonable starting budget for design discussion is N=3–5 with majority vote. Spatially distributing the redundant germs across the scene means a localized capture failure (e.g., focus blur over one region) cannot wipe an entire payload bit's set of germs.

### 5.2 Persistence-based confidence weighting (CRC-equivalent for detection + localization)

Persistent homology (gudhi or ripser, `06_DECODER_RESEARCH_PLAN.md` §3) gives each detected singularity a *persistence score* — a topological measure of how robustly that feature survives across scales. Low-persistence germs are weighted down in the decode vote; high-persistence germs are weighted up. This is the structural equivalent of CRC: detection of unreliable bits + localization to which germ-positions are unreliable + a continuous (rather than binary) confidence signal.

### 5.3 Sheaf-cohomology consistency check (linked-CRC-equivalent for global integrity)

Aurexis Core's `00_PROJECT_CORE/HIGHER_ORDER_COHERENCE_BRANCH_CAPSTONE_V1.md` (lines 17–47) ships a bounded executable sheaf-style composition framework: Overlap Detection (Bridge V1, 82 assertions), Local Section Consistency (Bridge V1, 62 assertions), Sheaf-Style Composition (Bridge V1, 58 assertions), Cohomological Obstruction Detection (Bridge V1, 56 assertions). The whole branch is COMPLETE-ENOUGH and capstone-verified.

For the phoxoidal carrier, these bridges check **neighbor-compatibility of detected germs** in the scene. If germ A says "here is a κ₁=0.7 cusp at position p" and germ B at neighboring position q says "here is a κ₁=-0.7 fold at p+ε," the sheaf composition step detects the obstruction (these two local sections cannot be glued into a coherent global assignment) and flags it. This is the structural analog of AXP6's neighborhood-linked CRC: a single corrupted germ propagates an obstruction into its neighborhood, making the failure pattern identifiable.

CRYPSOID flagged sheaf-theoretic neighbor compatibility maps as v0.4+ work in its own roadmap (`README.md` line 84). Aurexis Core has shipped it. **The composition is what makes the substrate change work as a substrate change rather than as a research project.**

## 6. Bit allocation per germ — the symbol encoding question

Layer 3 of §2 requires a concrete answer to "how many bits does one germ carry?" This is the question `05_INFORMATION_DENSITY_ANALYSIS.md` answers in the back-of-envelope sense; the architectural question is **what is the bit-allocation policy across the 5 coefficients?**

CRYPSOID's `tools/crypsorender/math/germ.py` (lines 105–168) clamps the 5 coefficients to physical ranges:

```python
max_kappa     = 25.0   # κ₁, κ₂
max_chi_omega = 50.0   # χ, ω
max_zeta      = 100.0  # ζ
```

Three honest options for symbol coding:

| Option | Description | Bits per germ | Pros / cons |
|---|---|---:|---|
| **Uniform 8-bit per coefficient** (handoff default) | Each of κ₁, κ₂, χ, ω, ζ quantized to 256 levels over its physical range | 40 | Simplest. Detection error in any coefficient flips ≤8 bits of payload. Even noise budget. |
| **Range-aware quantization** | Higher bits for κ-class (smaller range, more SNR), fewer bits for ζ (largest range, lowest robustness) | ~30–50 | Better fit to expected detection-noise distribution. Requires Phase 1 SNR measurement to set bit counts. |
| **VSA / hyperdimensional binding over germs** | Treat the 5-coefficient germ as a hypervector; bind multiple germs together via VSA superposition; decode via cleanup memory | Variable; potentially much higher per-germ density | Native fit with Aurexis Core's Branch 5 (`README.md` line 260). Requires substantial cleanup-memory infrastructure. Strongest theoretical density; least empirically validated for this use. |

For Phase 0 the proposal carries the handoff's 40-bit-per-germ assumption verbatim and notes the alternatives. Phase 1 must measure detection-noise per coefficient and choose. The choice does not affect the architecture; it affects the density.

## 7. Manifest placement in the new substrate

AXP6 places its manifest at known integer pixel coordinates in row 0 (`aurexis_decode.py` lines 272–284). The phoxoidal carrier cannot use that mechanism — there are no known integer pixel coordinates to place the manifest at, after capture warp.

The proposed substitute: **the manifest is encoded as a known-position germ cluster in the scene**, with a higher-redundancy and higher-bits-per-coefficient encoding than payload germs. The cluster is placed at a canonical scene-coordinate location (e.g., the centroid of a known marker pattern in Tier C), so the germ extractor's first job after detecting any coherent germ structure is to find the manifest cluster, decode it, and use its parameters (payload size, redundancy N, bit allocation, sha256, etc.) for the rest of the decode.

This is structurally analogous to a barcode quiet-zone + format-information region: it is a small, high-redundancy, known-shape region whose decoding is the entry point for the larger payload decoding. It is *not* an integer-pixel-coordinate region; it is a structural region defined by germ-cluster geometry. The germ extractor finds it the same way it finds any other germ — by structural detection, not pixel addressing.

The exact protocol for marker placement, redundancy budget for the manifest, and what to do if manifest decoding fails (re-try with broader scale-space search? bail with structured error?) is a Phase 1 deliverable, not a Phase 0 one.

## 8. What survives that AXP6 didn't have

Per the v4 handoff, with citation to the source for each affordance:

### 8.1 Carrier appearance is unconstrained

Already covered in §4 above. AXP6 carriers look like 2-bit-indexed noise (`aurexis_decode.py` line 84 — color type 3 at bit depth 2 is the only accepted PNG profile). Phoxoidal carriers look like whatever the Tier C field is rendered as. Real marketable difference, not just technical.

### 8.2 Resolution flexibility

CRYPSOID's renderer takes resolution as a runtime parameter (`tools/crypsorender/cli.py` documented in `docs/crypsorender_architecture.md` §"cli.py" — `crypsorender render --scene <ply|3dphox> --camera <yaml> --out <png>` with arbitrary output resolution). Re-render the same `.3dphox` scene at any resolution for any target display. AXP6 carriers are fixed at encode time (the PNG dimensions are baked into the manifest at `grid_width` offset 28, `aurexis_decode.py` lines 305 / 320).

### 8.3 Cross-modal extension

The same scene-format approach extends naturally to:
- **3D printed carriers.** A `.3dphox` scene IS a 3D scene. Materializing it as a 3D printed object with germ-bearing surface relief is a direct extension; no architectural change.
- **Video frames.** CRYPSOID's `tools/crypsorender/output/turntable.py` already renders sequential frames of a moving camera through a scene; each frame is a valid carrier. (Caveat: temporal redundancy across frames is its own design space — `09_OPEN_QUESTIONS.md` §7.)
- **Physical surfaces (engraving, fabric weave, embossing).** Speculative but architecturally available, since the substrate is structural rather than pixel-modular.

Pixel-grid encodings do not extend naturally to any of these. Each requires a substantial reformulation.

### 8.4 Native composition with HDC and sheaves

Both already in Aurexis Core v1 (Branch 5 and Branch 3 respectively, capstones verified). Hypervectors over germs and sheaves over germ neighborhoods are first-class operations on the new carrier, not bolted on after the fact. This is the substrate-level integration that the v3 additive-layer approach cannot match — v3 sits on top of AXP6, so it inherits AXP6's substrate constraints; the phoxoidal carrier sits on top of the same algebraic substrate Aurexis Core's branches already use.

## 9. Hard rules (carried over from the handoff and made specific to the architecture)

These constrain every implementation detail of the architecture:

### 9.1 No GPU dependencies, ever

CRYPSOID's `README.md` line 88: "**No GPU/CUDA dependencies, ever.** Forbidden: `torch`, `pytorch`, `cuda-toolkit`, any `nvidia-*` package, `gsplat`, `diff-gaussian-rasterization`, `nerfstudio`." This carries forward to the phoxoidal carrier verbatim. The decoder's persistent-homology library (gudhi or ripser) is CPU-only, the renderer is the same pure-numpy CRYPSOID renderer, and any optimization work happens via numba JIT or numpy vectorization, not via GPU offload.

### 9.2 Aurexis Core's gate-tracking discipline

Every milestone must produce a bridge-and-capstone artifact in the format of `00_PROJECT_CORE/HIGHER_ORDER_COHERENCE_BRANCH_CAPSTONE_V1.md` (numbered milestones, per-bridge assertion counts, branch-level capstone). `07_INTEGRATION_BRIDGES.md` proposes the bridge sequence in this format.

### 9.3 Aurexis Core's frozen V1 surface is untouchable

ACOR-1.1's release zip (`Aurexis/00_PROJECT_CORE/aurexis_core_v1_substrate_candidate_locked.zip`), all 33 git tags including `core-v1-substrate-candidate-or1.1`, all 26 backup branches matching `backup/v1-substrate-candidate-*` — frozen. The phoxoidal carrier work lands in the V2 research lane (or a new research lane Vince specifies — `09_OPEN_QUESTIONS.md` §8), never in v1's release surface.

### 9.4 Bit-exact contracts preserved

Brotli + SHA-256 + byte-identity decode requirement carry forward without exception. No "lossy mode" of the carrier exists. If the germ extractor cannot recover enough germs to reconstruct the payload bit-exactly, the carrier fails the decode honestly with a structured error — same posture as AXP6's `ValueError("Parity verification failed — data may be corrupted")`.

### 9.5 Provenance and IP discipline

CRYPSOID's `tools/crypsorender/math/germ.py` is Bug's. Aurexis Core's `00_PROJECT_CORE/` bridges and `06_PROOF_SYSTEM/aurexis_research_sim/` are Vince's. The composition produces a clearly-attributed result with terms TBD between partners (`09_OPEN_QUESTIONS.md` §5).

## 10. Architecture summary diagram (textual)

```
ENCODE
    payload bytes (any file)
        │
        ▼  [layer 1: payload]
    Brotli compress
        │
        ▼  [layer 2: inner header]
    prepend AXP6-equivalent header
        (magic + version + comp + sizes + sha256 + filename)
        │
        ▼  [layer 3: symbol encoding]
    chunk into N-bit-per-germ symbols (default N=40, 8 bits × 5 coefficients)
    add redundancy: each payload symbol → R germs (default R=3-5)
    add manifest cluster: high-redundancy, known-position germ block
        │
        ▼  [layer 4: scene assembly]
    place germs in 3D scene with Tier C aesthetic field
        Tier A/B = payload germs
        Tier C   = visible aesthetic (photograph/brand/etc.)
    output: .3dphox scene (CRYPSOID format, new VCAR magic)
        │
        ▼  [layer 5: render]
    crypsorender → 2D image at chosen resolution
        │
        ▼  [layer 6: display]
    PNG to disk, screen, print, fabric, etched surface, etc.

DECODE
    captured image (file from camera, scanner, screen capture, or direct PNG)
        │
        ▼  [layer 7: capture] -- introduces smooth coordinate transformations
        │
        ▼  [layer 8: germ extraction]
    detect catastrophe singularities at multiple scales
        toolbox: scale-space, persistent homology, Mumford-Shah,
                 inverted CRYPSOID germ-fit
    classify each detected singularity by 5-coef germ basis
    score by persistent-homology confidence
        │
        ▼  [layer 8.5: integrity check]
    sheaf-style composition over germ neighborhoods
    cohomological-obstruction detection per Aurexis Branch 3
    flag low-confidence germs and obstruction-detected regions
        │
        ▼  [layer 9: symbol decoding]
    decode manifest cluster first → recover payload size, redundancy R, hash, etc.
    redundancy-vote across R germs per payload symbol with persistence weighting
    assemble compressed payload
        │
        ▼  [layer 10: payload verification]
    strip inner header
    Brotli decompress
    sha256 verify
        │
        ▼
    original file bytes (or structured failure)
```

The encoder is steps 1–6 forward; the decoder is steps 7–10 backward. Layers 1, 2, 10 are AXP6 verbatim. Layers 4, 5 are CRYPSOID's existing format and renderer. Layer 8.5 is Aurexis Core's existing sheaf composition framework. **Layers 3, 8, 9 are the new code this proposal would build.**

---

**Cross-references.** The math claim that layer 8's invariance survives smooth capture transformations is in `04_DIFFEOMORPHISM_INVARIANCE_ARGUMENT.md`. The information-density numbers are in `05_INFORMATION_DENSITY_ANALYSIS.md`. The decoder research plan is in `06_DECODER_RESEARCH_PLAN.md`. The integration bridges are in `07_INTEGRATION_BRIDGES.md`. The honest tradeoffs are in `08_HONEST_TRADEOFFS.md`.
