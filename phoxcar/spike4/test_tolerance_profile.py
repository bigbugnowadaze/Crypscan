"""Spike-4 tolerance-profile harness.

Encodes a single payload via spike-3, then for every (noise_type, severity)
in `noise.NOISE_SWEEP`:
  1. Applies the noise to the rendered carrier.
  2. Saves the noisy variant as an 8-bit PNG.
  3. Runs spike-3's decoder against the noisy PNG.
  4. Records SHA-256 pass/fail, RS stats, residuals, decode error mode.

Aggregates per-condition results into a tolerance profile JSON in the
format of `00_PROJECT_CORE/CAPTURE_TOLERANCE_BRIDGE_V1_GATE_VERIFICATION.md`'s
"Tolerance Profile Summary" — namely, in_bounds_max and out_of_bounds_min
per noise type.
"""
from __future__ import annotations
import hashlib
import json
import sys
import time
from datetime import datetime
from pathlib import Path

import numpy as np
from PIL import Image

SPIKE4_DIR = Path(__file__).resolve().parent
SPIKE3_DIR = SPIKE4_DIR.parent / 'spike3'
sys.path.insert(0, str(SPIKE4_DIR))
sys.path.insert(0, str(SPIKE3_DIR))

import brotli
from encoder import encode, EncodeParams                       # noqa: E402
from decoder import decode_with_manifest                        # noqa: E402
from noise import NOISE_SWEEP                                    # noqa: E402


def make_payload(target_n_germs: int = 500) -> bytes:
    """Smaller payload than spike-3's gate (500 germs vs 1000) so the sweep
    runs in a few minutes total."""
    base = (
        "Phoxcar spike-4 tolerance profile payload. Each condition in the "
        "sweep applies a known photometric noise to the spike-3 rendered "
        "carrier, then runs the decoder. The aim is to characterize where "
        "the substrate's working envelope ends.\n"
    )
    rng = np.random.default_rng(seed=20260504)
    words = base.split()
    n_pad_words = max(int(target_n_germs * 21.9) // 7, 100)
    pad_words = [words[i % len(words)] for i in rng.integers(0, len(words), n_pad_words)]
    return (base + ' '.join(pad_words)).encode('utf-8')


def apply_noise_and_save(
    canvas: np.ndarray, noise_fn, severity, png_path: Path, seed: int = 12345
):
    """Apply `noise_fn(canvas, severity)` (or with seed if accepted) and save."""
    try:
        noisy = noise_fn(canvas, severity, seed=seed)
    except TypeError:
        noisy = noise_fn(canvas, severity)
    img8 = (np.clip(noisy, 0.0, 1.0) * 255.0 + 0.5).astype(np.uint8)
    Image.fromarray(img8, mode='L').save(png_path, format='PNG')
    return noisy


def run_one_condition(
    canvas: np.ndarray,
    noise_type: str,
    noise_fn,
    severity,
    sidecar_path: Path,
    expected_sha: bytes,
    out_dir: Path,
) -> dict:
    """Run a single (noise_type, severity) condition. Returns metrics dict."""
    safe_severity = str(severity).replace('-', 'm').replace('.', 'p')
    noisy_png = out_dir / f"noisy_{noise_type}_{safe_severity}.png"
    noisy_canvas = apply_noise_and_save(canvas, noise_fn, severity, noisy_png)

    t0 = time.perf_counter()
    error = None
    res = None
    try:
        res = decode_with_manifest(noisy_png, sidecar_path)
    except Exception as e:
        error = f"{type(e).__name__}: {e}"
    t = time.perf_counter() - t0

    if res is None:
        return {
            'noise_type': noise_type,
            'severity': severity,
            'sha256_ok': False,
            'decode_error': error,
            'wall_time_s': t,
        }
    sha_ok = bool(res.sha256_ok and res.sha256 == expected_sha)
    return {
        'noise_type': noise_type,
        'severity': severity,
        'sha256_ok': sha_ok,
        'decode_error': None,
        'rs_frames_corrected': int(res.rs_corrected_frames),
        'rs_frames_failed': len(res.rs_failed_frames),
        'rs_bytes_corrected': int(res.rs_corrected_bytes),
        'extract_residual_max': float(res.extract_residual_max),
        'extract_residual_mean': float(res.extract_residual_mean),
        'wall_time_s': t,
    }


def summarize_per_noise_type(results: list[dict]) -> list[dict]:
    """For each noise type, compute in_bounds_max and out_of_bounds_min."""
    by_type: dict[str, list[dict]] = {}
    for r in results:
        by_type.setdefault(r['noise_type'], []).append(r)

    summary = []
    for nt, rs in by_type.items():
        sevs = sorted(rs, key=lambda r: r['severity'] if isinstance(r['severity'], (int, float)) else 0)
        passing = [r['severity'] for r in sevs if r['sha256_ok']]
        failing = [r['severity'] for r in sevs if not r['sha256_ok']]
        # For symmetric noise types (brightness_shift) consider absolute severity
        # for bound semantics. For monotone-severe types (sigma, JPEG) sort
        # naturally.
        if nt == 'jpeg_roundtrip':
            # JPEG: lower Q is more severe. So in_bounds_max = lowest Q that PASSES;
            # out_of_bounds_min = highest Q that FAILS.
            in_bounds_extreme = min(passing) if passing else None
            out_of_bounds_extreme = max(failing) if failing else None
            severity_metric = "JPEG quality (lower is more severe)"
        elif nt in ('contrast_scale', 'gamma_correction'):
            # Symmetric around 1.0
            passing_abs = [abs(s - 1.0) for s in passing]
            failing_abs = [abs(s - 1.0) for s in failing]
            in_bounds_extreme = max(passing_abs) if passing_abs else None
            out_of_bounds_extreme = min(failing_abs) if failing_abs else None
            severity_metric = f"|severity - 1.0|"
        elif nt == 'brightness_shift':
            passing_abs = [abs(s) for s in passing]
            failing_abs = [abs(s) for s in failing]
            in_bounds_extreme = max(passing_abs) if passing_abs else None
            out_of_bounds_extreme = min(failing_abs) if failing_abs else None
            severity_metric = "|delta|"
        else:
            # gaussian_intensity, focus_blur, salt_and_pepper:
            # higher severity is worse.
            in_bounds_extreme = max(passing) if passing else None
            out_of_bounds_extreme = min(failing) if failing else None
            severity_metric = "severity (higher is more severe)"
        summary.append({
            'noise_type': nt,
            'severity_metric': severity_metric,
            'in_bounds_extreme_pass': in_bounds_extreme,
            'out_of_bounds_extreme_fail': out_of_bounds_extreme,
            'all_passing_severities': sorted(passing) if passing else [],
            'all_failing_severities': sorted(failing) if failing else [],
        })
    return summary


def main(target_n_germs: int = 500) -> int:
    print("=" * 70)
    print("  phoxcar spike-4 — synthetic photometric-noise tolerance profile")
    print("=" * 70)

    # 1. Encode once via spike-3.
    payload = make_payload(target_n_germs)
    expected_sha = hashlib.sha256(payload).digest()
    base_png = SPIKE4_DIR / 'results' / 'base_carrier_8bit.png'
    base_png.parent.mkdir(parents=True, exist_ok=True)
    print(f"\n  payload size       : {len(payload):,}")
    print(f"  expected sha256    : {expected_sha.hex()[:32]}...")

    print(f"\n  ENCODING via spike-3 (8-bit) ...")
    enc_manifest = encode(
        payload, "payload.txt", base_png,
        params=EncodeParams(pixel_bit_depth=8),
        sidecar=True,
    )
    print(f"    germs in carrier : {enc_manifest['n_germs']:,}")
    print(f"    PNG dimensions   : {enc_manifest['width']} x {enc_manifest['height']}")

    sidecar_path = base_png.with_suffix(base_png.suffix + '.manifest.json')
    canvas = np.asarray(Image.open(base_png), dtype=np.float32) / 255.0
    print(f"    base carrier loaded: {canvas.shape}")

    # 2. Sanity: decode the unperturbed carrier (must PASS).
    print(f"\n  SANITY: decode unperturbed carrier ...")
    sanity_res = decode_with_manifest(base_png, sidecar_path)
    sanity_ok = sanity_res.sha256_ok and sanity_res.sha256 == expected_sha
    print(f"    SHA-256 pass     : {sanity_ok}")
    if not sanity_ok:
        print("    ABORT: spike-3 baseline failed before noise applied")
        return 1

    # 3. Sweep all noise conditions.
    out_dir = SPIKE4_DIR / 'results' / 'noisy_carriers'
    out_dir.mkdir(parents=True, exist_ok=True)

    print(f"\n  SWEEPING noise conditions ...")
    results = []
    t_sweep = time.perf_counter()
    for noise_type, noise_fn, severities in NOISE_SWEEP:
        for sev in severities:
            res = run_one_condition(
                canvas, noise_type, noise_fn, sev,
                sidecar_path, expected_sha, out_dir,
            )
            results.append(res)
            sym = '✓' if res['sha256_ok'] else 'X'
            err = f"  ({res['decode_error']})" if res['decode_error'] else ''
            print(f"    [{sym}] {noise_type:<22} sev={sev!s:<8} "
                  f"{res['wall_time_s']:.2f}s{err}")
    print(f"  sweep wall time    : {time.perf_counter() - t_sweep:.1f}s")

    # 4. Per-noise summary.
    summary = summarize_per_noise_type(results)
    print()
    print("=" * 70)
    print("  PER-NOISE-TYPE SUMMARY")
    print("=" * 70)
    for s in summary:
        nt = s['noise_type']
        ib = s['in_bounds_extreme_pass']
        oob = s['out_of_bounds_extreme_fail']
        print(f"  {nt:<22} extreme pass = {ib!s:<8} extreme fail = {oob!s}")
    print("=" * 70)

    # 5. Persist tolerance profile.
    timestamp = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    profile = {
        'timestamp': timestamp,
        'spike_version': '4.0',
        'substrate': 'spike-3 sigmoid carrier @ 8-bit',
        'payload_size': len(payload),
        'n_germs': enc_manifest['n_germs'],
        'png_dimensions': [enc_manifest['width'], enc_manifest['height']],
        'expected_sha256': expected_sha.hex(),
        'baseline_pass': bool(sanity_ok),
        'conditions': results,
        'per_type_summary': summary,
    }
    out_json = SPIKE4_DIR / 'results' / f'tolerance_profile_{timestamp}.json'
    out_json.write_text(json.dumps(profile, indent=2))
    print(f"\n  full profile -> {out_json.relative_to(SPIKE4_DIR)}")

    return 0


if __name__ == '__main__':
    sys.exit(main())
