"""Spike-8A synthetic tolerance profile.

Sweeps GEOMETRIC noise (translation, rotation, scale, shear, perspective
tilt) and PHOTOMETRIC noise (Gaussian, JPEG, focus blur, gamma,
brightness, contrast, salt-pepper) against the spike-8A substrate.

For direct comparison: same photometric sweep as spikes 4/5/6/7. The new
geometric sweep is the spike-8A novelty — substrate must recover pose
from the captured image without sidecar.
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

SPIKE8A_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SPIKE8A_DIR))

import brotli
from encoder import encode, EncodeParams                       # noqa: E402
from decoder import decode                                       # noqa: E402
from noise import NOISE_SWEEP                                    # noqa: E402
from geometric_noise import GEOMETRIC_SWEEP                       # noqa: E402


def make_payload(target_n_germs: int = 200) -> bytes:
    base = (
        "Phoxcar spike-8A pose-recovery tolerance profile.\n"
        "Codebook + pilots + finders + manifest cluster.\n"
        "No JSON sidecar — decoder uses format spec only.\n"
    )
    rng = np.random.default_rng(seed=20260504)
    words = base.split()
    n_pad_words = max(int(target_n_germs * 4.4) // 7, 100)
    pad_words = [words[i % len(words)] for i in rng.integers(0, len(words), n_pad_words)]
    return (base + ' '.join(pad_words)).encode('utf-8')


def apply_geometric(canvas, fn, severity, png_path):
    noisy = fn(canvas, severity)
    img8 = (np.clip(noisy, 0.0, 1.0) * 255.0 + 0.5).astype(np.uint8)
    Image.fromarray(img8, mode='L').save(png_path, format='PNG')
    return noisy


def apply_photometric(canvas, fn, severity, png_path, seed=12345):
    try:
        noisy = fn(canvas, severity, seed=seed)
    except TypeError:
        noisy = fn(canvas, severity)
    img8 = (np.clip(noisy, 0.0, 1.0) * 255.0 + 0.5).astype(np.uint8)
    Image.fromarray(img8, mode='L').save(png_path, format='PNG')
    return noisy


def run_one(canvas, sweep_kind, name, fn, severity, expected_sha,
              out_dir, params):
    safe = str(severity).replace('-', 'm').replace('.', 'p')
    noisy_png = out_dir / f"{sweep_kind}_{name}_{safe}.png"
    if sweep_kind == 'geometric':
        apply_geometric(canvas, fn, severity, noisy_png)
    else:
        apply_photometric(canvas, fn, severity, noisy_png)
    t0 = time.perf_counter()
    res = decode(noisy_png, params=params)
    t = time.perf_counter() - t0
    return {
        'sweep': sweep_kind,
        'noise_type': name,
        'severity': severity,
        'sha256_ok': bool(res.sha256_ok),
        'finder_detection_ok': bool(res.finder_detection_ok),
        'decode_error': res.decode_error,
        'transform': res.transform.to_dict() if res.transform else None,
        'rs_corrected': int(res.rs_corrected_frames),
        'rs_failed': len(res.rs_failed_frames),
        'wall_time_s': t,
    }


def summarize(results):
    by_type = {}
    for r in results:
        key = (r['sweep'], r['noise_type'])
        by_type.setdefault(key, []).append(r)
    summary = []
    for (sweep, nt), rs in by_type.items():
        passing = [r['severity'] for r in rs if r['sha256_ok']]
        failing = [r['severity'] for r in rs if not r['sha256_ok']]
        summary.append({
            'sweep': sweep,
            'noise_type': nt,
            'passing': sorted(passing) if passing else [],
            'failing': sorted(failing) if failing else [],
        })
    return summary


def main(target_n_germs: int = 200) -> int:
    print("=" * 70)
    print("  phoxcar spike-8A — pose-recovery tolerance profile")
    print("=" * 70)

    payload = make_payload(target_n_germs)
    expected_sha = hashlib.sha256(payload).digest()
    base_png = SPIKE8A_DIR / 'results' / 'spike8a_base_carrier.png'
    base_png.parent.mkdir(parents=True, exist_ok=True)
    print(f"\n  payload size       : {len(payload):,}")
    print(f"  expected sha256    : {expected_sha.hex()[:32]}...")

    print(f"\n  ENCODING (codebook + pilots + finders + manifest, 8-bit) ...")
    t0 = time.perf_counter()
    info = encode(
        payload, "payload.txt", base_png,
        params=EncodeParams(pixel_bit_depth=8),
        sidecar=False,                                   # No sidecar — pure spec-driven
    )
    t_enc = time.perf_counter() - t0
    print(f"    canvas           : {info['canvas']}")
    print(f"    n_payload_germs  : {info['n_payload_germs']}")
    print(f"    encode wall time : {t_enc:.2f}s")

    canvas = np.asarray(Image.open(base_png), dtype=np.float32) / 255.0
    params = EncodeParams(pixel_bit_depth=8)

    print(f"\n  SANITY: decode unperturbed carrier ...")
    sanity = decode(base_png, params=params)
    sanity_ok = sanity.sha256_ok and sanity.sha256 == expected_sha
    print(f"    SHA-256 pass     : {sanity_ok}")
    print(f"    finder_ok        : {sanity.finder_detection_ok}")
    if not sanity_ok:
        print("    ABORT: spike-8A baseline failed before noise applied")
        return 1

    out_dir = SPIKE8A_DIR / 'results' / 'noisy_carriers'
    out_dir.mkdir(parents=True, exist_ok=True)

    results = []
    t_sweep = time.perf_counter()

    print(f"\n  GEOMETRIC SWEEP")
    for name, fn, severities in GEOMETRIC_SWEEP:
        for sev in severities:
            res = run_one(canvas, 'geometric', name, fn, sev, expected_sha, out_dir, params)
            results.append(res)
            sym = 'PASS' if res['sha256_ok'] else 'FAIL'
            f = 'F+' if res['finder_detection_ok'] else 'F-'
            err = f"  ({res['decode_error']})" if res['decode_error'] and not res['sha256_ok'] else ''
            print(f"    [{sym} {f}] {name:<20} sev={sev!s:<8} {res['wall_time_s']:.2f}s{err}")

    print(f"\n  PHOTOMETRIC SWEEP")
    for name, fn, severities in NOISE_SWEEP:
        for sev in severities:
            res = run_one(canvas, 'photometric', name, fn, sev, expected_sha, out_dir, params)
            results.append(res)
            sym = 'PASS' if res['sha256_ok'] else 'FAIL'
            f = 'F+' if res['finder_detection_ok'] else 'F-'
            err = f"  ({res['decode_error']})" if res['decode_error'] and not res['sha256_ok'] else ''
            print(f"    [{sym} {f}] {name:<20} sev={sev!s:<8} {res['wall_time_s']:.2f}s{err}")

    print(f"\n  total sweep wall time: {time.perf_counter() - t_sweep:.1f}s")

    summary = summarize(results)
    print()
    print("=" * 70)
    print("  PER-NOISE-TYPE SUMMARY")
    print("=" * 70)
    for s in summary:
        sweep, nt = s['sweep'], s['noise_type']
        print(f"  [{sweep:<11}] {nt:<22} pass={s['passing']!s} "
              f"fail={s['failing']!s}")
    print("=" * 70)

    timestamp = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    profile = {
        'timestamp': timestamp,
        'spike_version': '8A.0',
        'substrate': 'codebook + pilots + finders + manifest, no sidecar',
        'payload_size': len(payload),
        'n_payload_germs': info['n_payload_germs'],
        'canvas': info['canvas'],
        'expected_sha256': expected_sha.hex(),
        'baseline_pass': bool(sanity_ok),
        'conditions': results,
        'per_type_summary': summary,
    }
    out_json = SPIKE8A_DIR / 'results' / f'tolerance_profile_{timestamp}.json'
    out_json.write_text(json.dumps(profile, indent=2))
    print(f"\n  full profile -> {out_json.relative_to(SPIKE8A_DIR)}")
    return 0


if __name__ == '__main__':
    sys.exit(main())
