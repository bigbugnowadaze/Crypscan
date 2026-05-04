"""P3.B acceptance gate — phoxoidal-native pose recovery.

Same sweep as P3.A but with phoxoidal corner clusters + matched-filter
NCC detection in place of ArUco. Demonstrates how much of the V3
acceptance envelope can be met with a fully thesis-aligned substrate.

Acceptance targets (same as P3.A; per ChatGPT audit):
    translation:   arbitrary within frame
    rotation:      0-360°
    scale:         0.5 - 2.0×
    perspective tilt: up to 30°
    shear:         moderate (≤ 10°)
    sub-pixel offset: arbitrary
    rolling shutter: up to ~1 px/row
    JPEG: Q ≥ 50, ideally Q ≥ 15
    blur: σ ≤ 1.5 px
    gamma: 0.7 - 1.4
    brightness: ±0.10
    contrast: 0.6 - 1.4
    SHA-256: PASS

NCC matched-filter detection is INTRINSICALLY brightness/contrast-blind,
so we expect those to pass trivially. Gamma is the photometric channel
likely to break first (it warps within-template pixel ratios). Geometric
limits track NCC's tolerance to template deformation.
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

P3B_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(P3B_DIR))

import brotli
from encoder import encode, EncodeParams                       # noqa: E402
from decoder import decode                                       # noqa: E402
from noise import (                                              # noqa: E402
    gaussian_intensity, jpeg_roundtrip, focus_blur,
    gamma_correction, brightness_shift, contrast_scale,
    salt_and_pepper,
)
from geometric_noise import (                                    # noqa: E402
    translate, rotate, scale as scale_warp, shear,
    perspective_tilt, rolling_shutter,
)


# Acceptance gate sweeps — wider than spike-8A's
ACCEPTANCE_GEOMETRIC = [
    ("translation_x",  lambda img, sev: translate(img, dx=sev, dy=0),
     [0, 10, 30, 60, 100]),
    ("translation_y",  lambda img, sev: translate(img, dx=0, dy=sev),
     [0, 10, 30, 60, 100]),
    ("subpixel",       lambda img, sev: translate(img, dx=sev, dy=0),
     [0.0, 0.25, 0.5, 0.75]),
    ("rotation",       lambda img, sev: rotate(img, sev),
     [0, 5, 15, 30, 45, 90, 135, 180, 270]),
    ("scale",          lambda img, sev: scale_warp(img, sev),
     [0.5, 0.7, 0.85, 1.0, 1.18, 1.4, 1.7, 2.0]),
    ("shear",          lambda img, sev: shear(img, sev),
     [0, 2, 5, 10, 15]),
    ("tilt_x",         lambda img, sev: perspective_tilt(img, sev, axis='x'),
     [0, 5, 10, 20, 30, 40]),
    ("tilt_y",         lambda img, sev: perspective_tilt(img, sev, axis='y'),
     [0, 5, 10, 20, 30, 40]),
    ("rolling_shutter",lambda img, sev: rolling_shutter(img, sev),
     [0.0, 0.1, 0.3, 0.5, 1.0, 1.5]),
]

ACCEPTANCE_PHOTOMETRIC = [
    ("gaussian_intensity", lambda img, sev, seed=12345: gaussian_intensity(img, sev, seed=seed),
     [0.001, 0.005, 0.01, 0.02, 0.05, 0.10]),
    ("jpeg_roundtrip",     lambda img, sev: jpeg_roundtrip(img, sev),
     [95, 90, 75, 50, 30, 15]),
    ("focus_blur",         lambda img, sev: focus_blur(img, sev),
     [0.3, 0.6, 1.0, 1.5, 2.0]),
    ("gamma_correction",   lambda img, sev: gamma_correction(img, sev),
     [0.7, 0.85, 1.0, 1.18, 1.4]),
    ("brightness_shift",   lambda img, sev: brightness_shift(img, sev),
     [-0.10, -0.05, -0.02, 0.02, 0.05, 0.10]),
    ("contrast_scale",     lambda img, sev: contrast_scale(img, sev),
     [0.6, 0.7, 0.85, 1.0, 1.18, 1.4]),
    ("salt_and_pepper",    lambda img, sev, seed=12345: salt_and_pepper(img, sev, seed=seed),
     [0.001, 0.005, 0.01, 0.02, 0.05]),
]


def make_payload() -> bytes:
    base = (
        "Phoxcar P3.B acceptance gate payload.\n"
        "Phoxoidal-native corner clusters + matched-filter NCC + spike-7 substrate.\n"
    )
    rng = np.random.default_rng(seed=20260504)
    words = base.split()
    n_pad_words = max(int(200 * 4.4) // 7, 100)
    pad_words = [words[i % len(words)] for i in rng.integers(0, len(words), n_pad_words)]
    return (base + ' '.join(pad_words)).encode('utf-8')


def apply_and_save(canvas, fn, severity, png_path):
    try:
        warped = fn(canvas, severity)
    except TypeError:
        warped = fn(canvas, severity, seed=12345)
    img8 = (np.clip(warped, 0.0, 1.0) * 255.0 + 0.5).astype(np.uint8)
    Image.fromarray(img8, mode='L').save(png_path, format='PNG')
    return warped


def run_one(canvas, sweep_kind, name, fn, severity, expected_sha, out_dir, params):
    safe = str(severity).replace('-', 'm').replace('.', 'p')
    noisy_png = out_dir / f"{sweep_kind}_{name}_{safe}.png"
    apply_and_save(canvas, fn, severity, noisy_png)
    t0 = time.perf_counter()
    res = decode(noisy_png, params=params)
    t = time.perf_counter() - t0
    return {
        'sweep': sweep_kind,
        'noise_type': name,
        'severity': severity,
        'sha256_ok': bool(res.sha256_ok),
        'pose_ok': bool(res.pose_ok),
        'decode_error': res.decode_error,
        'transform': res.transform.to_dict() if res.transform else None,
        'rs_corrected': int(res.rs_corrected_frames),
        'rs_failed': len(res.rs_failed_frames),
        'wall_time_s': t,
    }


def summarize(results):
    by_type = {}
    for r in results:
        by_type.setdefault((r['sweep'], r['noise_type']), []).append(r)
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


def main() -> int:
    print("=" * 70)
    print("  phoxcar P3.B — phoxoidal-native fiducial acceptance gate")
    print("=" * 70)

    payload = make_payload()
    expected_sha = hashlib.sha256(payload).digest()
    base_png = P3B_DIR / 'results' / 'p3b_base_carrier.png'
    base_png.parent.mkdir(parents=True, exist_ok=True)
    print(f"\n  payload size       : {len(payload):,}")
    print(f"  expected sha256    : {expected_sha.hex()[:32]}...")

    print(f"\n  ENCODING (codebook + pilots + phoxoidal corner clusters + manifest, 8-bit) ...")
    info = encode(payload, "payload.txt", base_png,
                   params=EncodeParams(pixel_bit_depth=8))
    print(f"    canvas: {info['canvas']}, n_payload_germs: {info['n_payload_germs']}")

    canvas = np.asarray(Image.open(base_png), dtype=np.float32) / 255.0
    params = EncodeParams(pixel_bit_depth=8)

    print(f"\n  SANITY: decode unperturbed carrier ...")
    sanity = decode(base_png, params=params)
    sanity_ok = sanity.sha256_ok and sanity.sha256 == expected_sha
    print(f"    SHA-256 pass: {sanity_ok}")
    if not sanity_ok:
        print("    ABORT: P3.B baseline failed before noise applied")
        return 1

    out_dir = P3B_DIR / 'results' / 'sweep_carriers'
    out_dir.mkdir(parents=True, exist_ok=True)

    results = []
    t_sweep = time.perf_counter()

    print(f"\n  GEOMETRIC SWEEP")
    for name, fn, severities in ACCEPTANCE_GEOMETRIC:
        for sev in severities:
            res = run_one(canvas, 'geometric', name, fn, sev, expected_sha, out_dir, params)
            results.append(res)
            sym = 'PASS' if res['sha256_ok'] else 'FAIL'
            p = 'P+' if res['pose_ok'] else 'P-'
            err = f"  ({res['decode_error']})" if res['decode_error'] else ''
            print(f"    [{sym} {p}] {name:<20} sev={sev!s:<8} {res['wall_time_s']:.2f}s{err}")

    print(f"\n  PHOTOMETRIC SWEEP")
    for name, fn, severities in ACCEPTANCE_PHOTOMETRIC:
        for sev in severities:
            res = run_one(canvas, 'photometric', name, fn, sev, expected_sha, out_dir, params)
            results.append(res)
            sym = 'PASS' if res['sha256_ok'] else 'FAIL'
            p = 'P+' if res['pose_ok'] else 'P-'
            err = f"  ({res['decode_error']})" if res['decode_error'] else ''
            print(f"    [{sym} {p}] {name:<20} sev={sev!s:<8} {res['wall_time_s']:.2f}s{err}")

    print(f"\n  total sweep wall time: {time.perf_counter() - t_sweep:.1f}s")

    summary = summarize(results)
    print()
    print("=" * 70)
    print("  PER-NOISE-TYPE SUMMARY")
    print("=" * 70)
    for s in summary:
        print(f"  [{s['sweep']:<11}] {s['noise_type']:<22} pass={s['passing']!s} "
              f"fail={s['failing']!s}")
    print("=" * 70)

    timestamp = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    profile = {
        'timestamp': timestamp,
        'spike_version': 'P3B.0',
        'substrate': 'spike-7 codebook + pilots + phoxoidal-native corner clusters (NCC) @ 8-bit',
        'payload_size': len(payload),
        'n_payload_germs': info['n_payload_germs'],
        'canvas': info['canvas'],
        'expected_sha256': expected_sha.hex(),
        'baseline_pass': bool(sanity_ok),
        'conditions': results,
        'per_type_summary': summary,
    }
    out_json = P3B_DIR / 'results' / f'acceptance_profile_{timestamp}.json'
    out_json.write_text(json.dumps(profile, indent=2))
    print(f"\n  full profile -> {out_json.relative_to(P3B_DIR)}")
    return 0


if __name__ == '__main__':
    sys.exit(main())
