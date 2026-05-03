# refs/crypsoid/

CRYPSOID public repo: `https://github.com/bigbugnowadaze/CRYPSOID`

The Phase 0 package cites the following CRYPSOID files. Clone the repo and read at the cited paths to verify.

| Path in CRYPSOID repo | What the proposal cites it for |
|---|---|
| `README.md` | Project framing; phoxoidal vs Gaussian thesis; PhoxBench Tier 1 result; no-GPU rule (line 88); honest density numbers (lines 46–60) |
| `docs/FORMAT.md` | `.3dphox` format spec — magic / manifest / chunk encoding; tier semantics (Tier A native render, Tier B native exact, Tier C fallback); v0.4 planned germ chunks (`germ_5coef_f16`, `germ_index_u32`); `CRYPSOID40\0` magic |
| `docs/crypsorender_architecture.md` | Renderer module structure; `SplatBuffer` schema; tier-aware dispatch in the rasterizer; honesty caveats |
| `docs/thesis_digest.md` | The phoxoidal-vs-Gaussian thesis (line 11); two-layer math (Φ gauge + caustic-chart action); 5-coefficient germ basis with κ₁/κ₂/χ/ω/ζ semantics; tier semantics; killer metric |
| `docs/ROADMAP.md` | Phase ladder (Tier 0 done, Tier 1 in progress, Tier 2 planned); v0.4+ work queue (sheaf maps, native germ chunks); v31/v32/v33/v34/v40+ format extensions |
| `reports/TIER_1_results.md` | The 2.0× killer-ratio result on four real meshes; what it claims and what it does not claim (lines 60–82) |
| `reports/PROJECT_STATE.md` | Running status; engineering history; what is and is not verified |
| `tools/crypsorender/math/germ.py` | The 5-coefficient germ basis (lines 23–30); forward Newton solver `closest_point_on_germ()` (lines 54–95); synthetic germ fitter `fit_synthetic_germs_5()` (lines 105–168); coefficient bounds (lines 162–166) |
| `tools/crypsorender/io/phox_loader.py` | `.3dphox` reader (~250 LoC) — useful for understanding what the format spec produces in code |
| `tools/img2phox/` (full directory; 26 files, 5,872 lines) | The image → 3D phoxoidal scene reconstruction pipeline. See `ADDENDUM_01_img2phox_integration.md` for the full inventory. Cited heavily by the addendum; not by the original Phase 0 package because the directory was not present in the clone Phase 0 was authored against. |
| `docs/img2phox_spec.md` | Authoritative spec for the image→`.3dphox` compiler (Phase F). Cited in `ADDENDUM_01_img2phox_integration.md` §2. |
| `docs/v40_native_germ_chunks_spec.md` | v40 format extension for native germ chunks (`germ_5coef_f16`, `germ_index_u32`). Referenced in `03_PHOXOIDAL_CARRIER_ARCHITECTURE.md` §2 layer 4 and `ADDENDUM_01` §2.3. |

## On the original Phase 0 note about `tools/img2phox/`

An earlier version of this index noted that `tools/img2phox/` did not exist in the CRYPSOID clone Phase 0 was authored against. That note was correct at the time and is now superseded — the directory is present in the current CRYPSOID HEAD as of 2026-05-03. The addendum (`ADDENDUM_01_img2phox_integration.md`) reflects the corrected state and re-scopes Phase 1 estimates accordingly.
