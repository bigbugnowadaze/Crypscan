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

## Notes on the user's "tools/img2phox/" reference

The user's task description mentioned reading "tools/img2phox/" thoroughly. CRYPSOID's `tools/` does not contain a directory of that exact name. The closest equivalents are:

- `tools/crypsorender/` — the renderer (~1,600 LoC pure numpy), with subdirectories `io/`, `math/`, `pipeline/`, `output/`. This is the forward-direction (scene → image) tool.
- `tools/phoxbench/` — the benchmark harness for the killer-ratio measurement.
- `recovery_v2/tools/phoxoid_convert.py` — referenced in `docs/thesis_digest.md` line 109 as the v0 PLY→`.phox.json` converter (a fitting tool, not an image extractor).

The Phase 0 package read all three of the above plus the cited `docs/` and `reports/` files. If the user meant a specific other directory, it isn't in the public repo as of the cloned commit and the user should clarify.
