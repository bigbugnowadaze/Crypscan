# phoxcar/spike4 — synthetic photometric-noise tolerance profile

**Status:** in-progress
**Authorized:** 2026-05-03 (Bug)
**Predecessors:** `../spike/`, `../spike2/`, **`../spike3/`** (the substrate this builds on)
**Goal:** measure spike-3's decode success rate under simulated camera-pipeline photometric noise. Produces a tolerance profile in the format of Aurexis Core's `00_PROJECT_CORE/CAPTURE_TOLERANCE_BRIDGE_V1_GATE_VERIFICATION.md`.

This is the leading indicator of V3 viability — *before* committing to real captured-image work — and the natural follow-on to spike-3's clean 8-bit pass.

## Scope (intensity-domain noise only)

Spike-4 sweeps these noise types at multiple severities. Each is applied to the spike-3 rendered carrier between encode and decode; the rest of the pipeline (Brotli, AXP6 header, RS, sigmoid forward, linear LSQ inverse) is unchanged.

| Noise type | Severities | What it simulates |
|---|---|---|
| Additive Gaussian intensity noise | σ ∈ {0.001, 0.005, 0.01, 0.02, 0.05, 0.10} | Sensor read noise |
| JPEG round-trip | Q ∈ {95, 90, 75, 50, 30, 15} | Camera JPEG encoder |
| Gaussian focus blur | kernel σ ∈ {0.3, 0.6, 1.0, 1.5, 2.0} px | Imperfect focus |
| Gamma correction drift | γ ∈ {0.7, 0.85, 1.0, 1.18, 1.4} | Monitor gamma mismatch |
| Brightness shift | Δ ∈ {-0.10, -0.05, -0.02, +0.02, +0.05, +0.10} | Exposure error |
| Contrast scaling | k ∈ {0.7, 0.85, 1.0, 1.18, 1.4} | AWB / contrast drift |
| Salt-and-pepper | rate ∈ {0.001, 0.005, 0.01, 0.02, 0.05} | Bad sensor pixels / thumbnail artifacts |

For each (noise_type, severity), spike-4 records:
- **SHA-256 pass/fail** — the binary gate.
- **Decode error mode** — exception type if decode fails (Brotli error, AXP6 magic mismatch, etc.).
- **RS frames corrected / failed** — load on the ECC layer.
- **Extract residual (max / mean)** — fit accuracy degradation.
- **Wall time** — sanity check; spike-3 was 0.40 s without noise.

## Out of scope (deferred to spike-5 / Phase 1 P3 manifest cluster bridge)

**Geometric** transformations require manifest-cluster bootstrap to recover the displaced germ positions. Spike-3 ships a JSON sidecar with germ positions; that approach can't survive geometric transforms. Spike-5 should add a structural manifest cluster, then characterize:

- Sub-pixel translation (offset in {0.5, 1.0, 2.0} px)
- Perspective tilt (angles in {5°, 10°, 20°, 30°})
- Rotation (in {5°, 10°, 30°, 90°})
- Scale (in {0.7, 0.9, 1.1, 1.3})
- Rolling shutter shear (per-row shift in {0.1, 0.5, 1.0} px/row)

Documenting this as out-of-scope keeps spike-4 tight and the photometric tolerance profile clean.

## Acceptance criterion

Spike-4 is a **measurement** spike, not a pass/fail one. The deliverable is the tolerance profile JSON itself. The decision is what tolerance bounds the spike's substrate actually supports — those bounds inform Phase 1 P3 (decoder design), P4 (capture protocol envelope), and the V3 frontier discussion.

The profile's structure mirrors `V1_TOLERANCE_PROFILE` (`CAPTURE_TOLERANCE_BRIDGE_V1_GATE_VERIFICATION.md` §"Tolerance Profile Summary"):

```json
{
  "noise_type": "gaussian_intensity",
  "in_bounds_max":  0.02,    // max severity at which SHA-256 still passes
  "out_of_bounds_min": 0.05, // min severity at which SHA-256 fails
  "transitional_severities": [0.03, 0.04, ...]   // mixed pass/fail
}
```

## Files

| File | Purpose |
|---|---|
| `noise.py` | NEW — pure-numpy photometric noise functions |
| `test_tolerance_profile.py` | NEW — encode once, sweep noise, decode each, aggregate |
| `results/SPIKE4_REPORT.md` | created on test run |
| `results/tolerance_profile.json` | machine-readable per-condition results |

Spike-4 imports spike-3's encode/decode directly:

```python
sys.path.insert(0, str(SPIKE_DIR.parent / 'spike3'))
from encoder import encode, EncodeParams
from decoder import decode_with_manifest
```

## How to run

```bash
cd phoxcar/spike4
python3 test_tolerance_profile.py    # full sweep; ~minutes
```

Output: `results/SPIKE4_REPORT.md` + `results/tolerance_profile.json`.
