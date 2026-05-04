# phoxcar/spike8b — real-camera validation harness

**Status:** harness ready; awaiting capture session
**Authored:** 2026-05-04 (after PR #11 / P3.A + P3.B)
**Purpose:** characterize the **real-world** envelope of the V1 substrate
(P3.A — ArUco fiducials + spike-7 codebook) by decoding actual phone
captures of carriers displayed on actual screens.

This is the most important experiment in Phase 1. P3.A and P3.B both
showed strong synthetic envelopes; spike-8B tells us whether those
envelopes survive contact with real cameras and real screens.

---

## What spike-8B is

> "synthetic warps tell us what the algorithm *should* survive. Spike-8B
> tells us what the algorithm *actually* survives."

Three deliverables:
1. **`reference_carrier.png`** — the deterministic carrier the partnership
   displays on each test screen (committed; SHA-256 in `reference_carrier.info.json`).
2. **Capture protocol** (`CAPTURE_PROTOCOL.md`) — phone × screen × distance
   × angle × lighting matrix, ~50-80 captures, ~2 hours of partnership work.
3. **Analysis pipeline** (`analyze.py` + `report.py`) — ingests captures,
   runs P3.A decode, aggregates into a Markdown report.

## Workflow

```
                                                            (committed, deterministic)
  python3 generate_reference.py   ────────────────►  reference_carrier.png
                                                            │
                                                            ▼ (display + photograph)
                                                    captures/raw/*.jpg
                                                            │
                                                            ▼ (P3.A decode + auto-crop fallback)
  python3 analyze.py              ────────────────►  results/spike8b_results.json
                                                            │
                                                            ▼ (aggregate by axis)
  python3 report.py               ────────────────►  results/SPIKE8B_REPORT.md
```

## Step-by-step

### Recommended: solo quick pass (~30-45 min, one phone)

1. **Read** the "Solo quick pass" section of `CAPTURE_PROTOCOL.md`.
2. **Display** `reference_carrier.png` full-screen on any decent screen,
   max brightness, no filters.
3. **Take 9 captures** with one phone (e.g. S21 FE) per the solo matrix.
4. **Drop** captures into `captures/raw/` with names like
   `s21fe_msi_comfy_headon_bright_01.jpg`. (`captures/raw/` is gitignored.)
5. **Run** `python3 analyze.py && python3 report.py` from this directory.
6. **Commit** `results/SPIKE8B_REPORT.md` and `results/spike8b_results.json`.
7. **Tell Claude.** Report decides whether the full matrix is needed.

### Full matrix (only if solo pass surfaces something)

Same flow, but multiple phones × multiple screens. ~2 hours. Don't pre-commit;
let the solo data decide.

## What success looks like

After the **solo pass** (9 captures, one phone, one screen):
- **9/9 PASS** → real-world envelope is fine. P3.C is research luxury, not blocker.
  The full matrix is probably unnecessary; V1 ships on P3.A as-is.
- **7-8/9 PASS** with one concentrated failure → targeted follow-up captures
  beat a full matrix. One more solo session may be enough.
- **4-6/9 PASS** → real-world is meaningfully harder than synthetic. Worth a
  full multi-phone × multi-screen session to characterize.
- **<4/9 PASS** → P3.A has a real-world brittleness we didn't predict.
  Investigate before any further captures.

## Files

| File | Purpose |
|---|---|
| `reference_carrier.png` | the deterministic 1280×1280 carrier to display |
| `reference_carrier.info.json` | encoder params + expected payload SHA-256 |
| `generate_reference.py` | re-creates the reference carrier (idempotent) |
| `CAPTURE_PROTOCOL.md` | partnership-facing capture instructions |
| `analyze.py` | decode each capture, log per-capture results |
| `report.py` | aggregate the JSON into a human-readable Markdown report |
| `captures/raw/` | gitignored — partnership's photos go here |
| `captures/processed/` | gitignored — analyze.py's intermediate PNGs |
| `results/SPIKE8B_REPORT.md` | the final per-axis report (committed when generated) |
| `results/spike8b_results.json` | per-capture machine-readable results (committed) |

## What's NOT in scope

- **P3.B real-camera validation.** P3.B v0 has known synthetic gaps
  (rotation, rolling shutter); validating its real-world behavior is a
  follow-up (`spike8b_p3b/` could be authorized later).
- **Multi-payload variation.** Spike-8B uses ONE reference carrier with ONE
  payload. Payload variation isn't the unknown here; capture conditions are.
- **Decoder performance / runtime.** Spike-8B is correctness validation. Speed
  optimization comes after.

## Reproduce / re-generate

```bash
pip install brotli reedsolo numpy scipy Pillow scikit-image opencv-python
cd phoxcar/spike8b
python3 generate_reference.py    # regenerates reference_carrier.png
python3 analyze.py               # after dropping captures into captures/raw/
python3 report.py                # after analyze.py
```
