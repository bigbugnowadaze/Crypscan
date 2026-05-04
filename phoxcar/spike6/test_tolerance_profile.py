"""Spike-6 tolerance profile — same noise sweep as spike-4 / spike-5,
applied to the spike-6 codebook-modulation substrate.

For direct comparison: same payload size target, same noise types, same
severities. Difference is ONLY in the substrate's symbol channel design:
8-bits-per-germ via 256-glyph codebook + nearest-neighbor decode, vs
spike-4's 40-bits-per-germ continuous + spike-5's R=3 + RS(255, 191).
"""
from __future__ import annotations
import hashlib
import json
import sys
import time
from datetime import datetime
from pathlib import Path

import numpy as np
import brotli
from PIL import Image

SPIKE6_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SPIKE6_DIR))

from encoder import encode, EncodeParams                       # noqa: E402
from decoder import decode_with_manifest                        # noqa: E402
from noise import NOISE_SWEEP                                    # noqa: E402


def make_payload(target_n_germs: int = 1000) -> bytes:
    """Build a payload whose post-Brotli + AXP6 + RS expansion produces
    roughly target_n_germs germs (1 byte/germ).
    """
    base = (
        "Phoxcar spike-6 codebook-modulation tolerance profile payload.\n"
        "256-glyph codebook + nearest-neighbor decode in c_ortho space.\n"
        "Same noise sweep as spike-4/5 for direct comparison.\n"
    )
    rng = np.random.default_rng(seed=20260504)
    words = base.split()
    # Brotli on varied text gives ~ 0.20 ratio; RS adds ~14%; 1 byte/germ.
    # So source size ~= target_n_germs / 0.20 / 1.14 ~= target_n_germs * 4.4.
    n_pad_words = max(int(target_n_germs * 4.4) // 7, 100)
    pad_words = [words[i % len(words)] for i in rng.integers(0, len(words), n_pad_words)]
    return (base + ' '.join(pad_words)).encode('utf-8')


def apply_noise_and_save(canvas, noise_fn, severity, png_path, seed=12345):
    try:
        noisy = noise_fn(canvas, severity, seed=seed)
    except TypeError:
        noisy = noise_fn(canvas, severity)
    img8 = (np.clip(noisy, 0.0, 1.0) * 255.0 + 0.5).astype(np.uint8)
    Image.fromarray(img8, mode='L').save(png_path, format='PNG')
    return noisy


def run_one_condition(canvas, noise_type, noise_fn, severity,
                       sidecar_path, expected_sha, out_dir):
    safe = str(severity).replace('-', 'm').replace('.', 'p')
    noisy_png = out_dir / f"noisy_{noise_type}_{safe}.png"
    apply_noise_and_save(canvas, noise_fn, severity, noisy_png)
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
            'noise_type': noise_type, 'severity': severity,
            'sha256_ok': False, 'decode_error': error,
            'wall_time_s': t,
        }
    return {
        'noise_type': noise_type, 'severity': severity,
        'sha256_ok': bool(res.sha256_ok and res.sha256 == expected_sha),
        'decode_error': None,
        'rs_frames_corrected': int(res.rs_corrected_frames),
        'rs_frames_failed': len(res.rs_failed_frames),
        'rs_bytes_corrected': int(res.rs_corrected_bytes),
        'extract_residual_max': float(res.extract_residual_max),
        'extract_residual_mean': float(res.extract_residual_mean),
        'nn_margin_min': float(res.nn_margin_min),
        'nn_margin_mean': float(res.nn_margin_mean),
        'wall_time_s': t,
    }


def summarize(results):
    by_type = {}
    for r in results:
        by_type.setdefault(r['noise_type'], []).append(r)
    summary = []
    for nt, rs in by_type.items():
        passing = [r['severity'] for r in rs if r['sha256_ok']]
        failing = [r['severity'] for r in rs if not r['sha256_ok']]
        if nt == 'jpeg_roundtrip':
            in_b = min(passing) if passing else None
            oob_b = max(failing) if failing else None
        elif nt in ('contrast_scale', 'gamma_correction'):
            p_abs = [abs(s - 1.0) for s in passing]
            f_abs = [abs(s - 1.0) for s in failing]
            in_b = max(p_abs) if p_abs else None
            oob_b = min(f_abs) if f_abs else None
        elif nt == 'brightness_shift':
            p_abs = [abs(s) for s in passing]
            f_abs = [abs(s) for s in failing]
            in_b = max(p_abs) if p_abs else None
            oob_b = min(f_abs) if f_abs else None
        else:
            in_b = max(passing) if passing else None
            oob_b = min(failing) if failing else None
        summary.append({
            'noise_type': nt,
            'in_bounds_extreme_pass': in_b,
            'out_of_bounds_extreme_fail': oob_b,
            'all_passing_severities': sorted(passing) if passing else [],
            'all_failing_severities': sorted(failing) if failing else [],
        })
    return summary


def main(target_n_germs: int = 1000) -> int:
    print("=" * 70)
    print("  phoxcar spike-6 — codebook modulation tolerance profile")
    print("=" * 70)

    payload = make_payload(target_n_germs)
    expected_sha = hashlib.sha256(payload).digest()
    base_png = SPIKE6_DIR / 'results' / 'spike6_base_carrier.png'
    base_png.parent.mkdir(parents=True, exist_ok=True)
    print(f"\n  payload size       : {len(payload):,}")
    print(f"  expected sha256    : {expected_sha.hex()[:32]}...")

    print(f"\n  ENCODING (256-glyph codebook, 8-bit) ...")
    t0 = time.perf_counter()
    enc_manifest = encode(
        payload, "payload.txt", base_png,
        params=EncodeParams(pixel_bit_depth=8),
        sidecar=True,
    )
    t_enc = time.perf_counter() - t0
    print(f"    PNG dimensions   : {enc_manifest['width']} x {enc_manifest['height']}")
    print(f"    germs in carrier : {enc_manifest['n_germs']:,}  (1 byte/germ)")
    print(f"    rs_encoded_size  : {enc_manifest['rs_encoded_size']:,}")
    print(f"    encode wall time : {t_enc:.2f}s")

    sidecar_path = base_png.with_suffix(base_png.suffix + '.manifest.json')
    canvas = np.asarray(Image.open(base_png), dtype=np.float32) / 255.0

    print(f"\n  SANITY: decode unperturbed carrier ...")
    sanity_res = decode_with_manifest(base_png, sidecar_path)
    sanity_ok = sanity_res.sha256_ok and sanity_res.sha256 == expected_sha
    print(f"    SHA-256 pass     : {sanity_ok}")
    print(f"    NN margin        : min={sanity_res.nn_margin_min:.3f}, "
          f"mean={sanity_res.nn_margin_mean:.3f}")
    print(f"    RS               : corrected={sanity_res.rs_corrected_frames}, "
          f"failed={len(sanity_res.rs_failed_frames)}")
    if not sanity_ok:
        print("    ABORT: spike-6 baseline failed before noise applied")
        return 1

    out_dir = SPIKE6_DIR / 'results' / 'noisy_carriers'
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
            sym = 'PASS' if res['sha256_ok'] else 'FAIL'
            err = f"  ({res['decode_error']})" if res['decode_error'] else ''
            extra = ''
            if 'nn_margin_min' in res:
                extra = (f"  NN_min={res['nn_margin_min']:.3f}  "
                         f"RS_corr={res['rs_frames_corrected']}/{res.get('rs_frames_failed', 0)}f")
            print(f"    [{sym}] {noise_type:<22} sev={sev!s:<8} "
                  f"{res['wall_time_s']:.2f}s{err}{extra}")
    print(f"  sweep wall time    : {time.perf_counter() - t_sweep:.1f}s")

    summary = summarize(results)
    print()
    print("=" * 70)
    print("  PER-NOISE-TYPE SUMMARY")
    print("=" * 70)
    for s in summary:
        nt = s['noise_type']
        ib = s['in_bounds_extreme_pass']
        oob = s['out_of_bounds_extreme_fail']
        print(f"  {nt:<22} extreme pass = {ib!s:<10} extreme fail = {oob!s}")
    print("=" * 70)

    timestamp = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    profile = {
        'timestamp': timestamp,
        'spike_version': '6.0',
        'substrate': 'sigmoid carrier + 256-glyph codebook + nearest-neighbor decode @ 8-bit',
        'payload_size': len(payload),
        'n_germs': enc_manifest['n_germs'],
        'png_dimensions': [enc_manifest['width'], enc_manifest['height']],
        'expected_sha256': expected_sha.hex(),
        'baseline_pass': bool(sanity_ok),
        'conditions': results,
        'per_type_summary': summary,
    }
    out_json = SPIKE6_DIR / 'results' / f'tolerance_profile_{timestamp}.json'
    out_json.write_text(json.dumps(profile, indent=2))
    print(f"\n  full profile -> {out_json.relative_to(SPIKE6_DIR)}")
    return 0


if __name__ == '__main__':
    sys.exit(main())
