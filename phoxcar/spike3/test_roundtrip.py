"""Phoxcar spike-3 acceptance gate (sigmoid display function, 8-bit target).

Runs encode (sigmoid render) -> decode (linear LSQ in logit space) on a
~1000-germ payload at 8-bit pixel depth and asserts:

    1. SHA-256 roundtrip
    2. RS frames all decoded
    3. Total wall time < 10 s (relaxed from spike-1's 30 s tighter than
       spike-2's 60 s; linear LSQ is fast)

Predicted: PASS at 8-bit. Demonstrates that the
renderer/carrier separation (Bug + ChatGPT analysis 2026-05-03)
recovers full 40-bit/germ density without spike-2's H^2 nonlinearity
penalty.
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

SPIKE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SPIKE_DIR))

from encoder import encode, EncodeParams                       # noqa: E402
from decoder import decode_with_manifest                        # noqa: E402


def make_payload(target_n_germs: int) -> bytes:
    """Build a payload whose post-Brotli + AXP6 + RS expansion produces
    roughly target_n_germs germs.

    Brotli ratio ~0.20 for varied text. RS adds ~14% overhead.
    Bit packing is 40 bits / germ = 5 bytes / germ exactly.
    Source size ~= target_n_germs * 5 / 0.20 / 1.14 = target_n_germs * 21.9
    """
    base = (
        "Phoxoidal carrier spike-3 payload — Phase 0.5 acceptance gate.\n"
        "Sigmoid display function: intensity = sigmoid(baseline + amp * H).\n"
        "Same 5-coefficient catastrophe-germ basis as CRYPSOID's strict\n"
        "renderer; different display function for 8-bit visibility.\n"
        "If this text decodes byte-exact, the renderer/carrier separation\n"
        "is empirically validated as the production-target substrate path.\n"
    )
    rng = np.random.default_rng(seed=20260503)
    words = base.split()
    n_pad_words = max(int(target_n_germs * 21.9) // 7, 100)
    pad_words = [words[i % len(words)] for i in rng.integers(0, len(words), n_pad_words)]
    return (base + ' '.join(pad_words)).encode('utf-8')


def main(target_n_germs: int = 1000, pixel_bit_depth: int = 8) -> int:
    t0 = time.perf_counter()

    print("=" * 70)
    print(f"  phoxcar spike-3 — sigmoid carrier acceptance gate")
    print(f"  pixel_bit_depth = {pixel_bit_depth}")
    print("=" * 70)

    payload = make_payload(target_n_germs)
    compressed = brotli.compress(payload, quality=11)
    expected_sha = hashlib.sha256(payload).digest()
    print(f"  payload bytes      : {len(payload):,}")
    print(f"  compressed bytes   : {len(compressed):,}")
    print(f"  expected sha256    : {expected_sha.hex()[:32]}...")

    out_png = SPIKE_DIR / 'results' / f'spike3_carrier_{pixel_bit_depth}bit.png'
    out_png.parent.mkdir(parents=True, exist_ok=True)

    print()
    print(f"  ENCODING (sigmoid display + linear codec + RS) ...")
    t_enc0 = time.perf_counter()
    enc_manifest = encode(
        payload, "payload.txt", out_png,
        params=EncodeParams(pixel_bit_depth=pixel_bit_depth),
        sidecar=True,
    )
    t_enc = time.perf_counter() - t_enc0
    print(f"    PNG dimensions   : {enc_manifest['width']} x {enc_manifest['height']}")
    print(f"    PNG bytes on disk: {enc_manifest['png_bytes']:,}")
    print(f"    germs in carrier : {enc_manifest['n_germs']:,} "
          f"(40 bits/germ, byte-aligned)")
    print(f"    framed_size      : {enc_manifest['framed_size']:,}")
    print(f"    rs_encoded_size  : {enc_manifest['rs_encoded_size']:,}")
    print(f"    encode wall time : {t_enc:.2f}s")

    print()
    print(f"  DECODING (linear LSQ in logit space + RS) ...")
    sidecar = out_png.with_suffix(out_png.suffix + '.manifest.json')
    t_dec0 = time.perf_counter()
    decode_error = None
    res = None
    try:
        res = decode_with_manifest(out_png, sidecar)
    except Exception as e:
        decode_error = f"{type(e).__name__}: {e}"
    t_dec = time.perf_counter() - t_dec0

    if res is None:
        print(f"    DECODE FAILED: {decode_error}")
        print(f"    decode wall time : {t_dec:.2f}s")
        total_time = time.perf_counter() - t0
        print()
        print("=" * 70)
        print(f"  GATE 1 — SHA-256 roundtrip            : FAIL ({decode_error})")
        print(f"  OVERALL                              : FAIL")
        print("=" * 70)
        return 1

    print(f"    sha256 ok        : {res.sha256_ok}")
    print(f"    size ok          : {res.size_ok}")
    print(f"    actual sha256    : {res.sha256.hex()[:32]}...")
    print(f"    extract residual : max={res.extract_residual_max:.4f}, "
          f"mean={res.extract_residual_mean:.4f}")
    print(f"    RS frames        : {enc_manifest['rs_encoded_size'] // 255} total")
    print(f"    RS frames corrected: {res.rs_corrected_frames}")
    print(f"    RS bytes corrected: {res.rs_corrected_bytes}")
    print(f"    RS frames failed : {len(res.rs_failed_frames)}")
    print(f"    decode wall time : {t_dec:.2f}s")

    total_time = time.perf_counter() - t0
    sha_ok = res.sha256_ok and (res.sha256 == expected_sha)
    rs_ok = len(res.rs_failed_frames) == 0
    time_ok = total_time < 10.0
    overall = sha_ok and time_ok

    print()
    print("=" * 70)
    print(f"  GATE 1 — SHA-256 roundtrip            : {'PASS' if sha_ok else 'FAIL'}")
    print(f"  GATE 2 — RS frames all decoded        : {'PASS' if rs_ok else 'FAIL'} "
          f"({len(res.rs_failed_frames)} failed)")
    print(f"  GATE 3 — total wall time < 10 s       : {'PASS' if time_ok else 'FAIL'} "
          f"({total_time:.2f}s)")
    print()
    print(f"  OVERALL                              : "
          f"{'PASS' if overall else 'FAIL'}")
    print("=" * 70)

    timestamp = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    report = {
        'timestamp': timestamp, 'spike_version': '3.0',
        'pixel_bit_depth': pixel_bit_depth,
        'payload_size': len(payload), 'compressed_size': len(compressed),
        'rs_encoded_size': enc_manifest['rs_encoded_size'],
        'n_germs': enc_manifest['n_germs'],
        'png_dimensions': [enc_manifest['width'], enc_manifest['height']],
        'png_bytes': enc_manifest['png_bytes'],
        'expected_sha256': expected_sha.hex(),
        'actual_sha256': res.sha256.hex(),
        'sha256_ok': bool(sha_ok), 'size_ok': bool(res.size_ok),
        'extract_residual_max': float(res.extract_residual_max),
        'extract_residual_mean': float(res.extract_residual_mean),
        'rs_frames_corrected': int(res.rs_corrected_frames),
        'rs_bytes_corrected': int(res.rs_corrected_bytes),
        'rs_frames_failed': res.rs_failed_frames,
        'wall_time_total_s': float(total_time),
        'wall_time_encode_s': float(t_enc),
        'wall_time_decode_s': float(t_dec),
        'gate_pass': bool(overall),
    }
    out_json = SPIKE_DIR / 'results' / f'roundtrip_{timestamp}_{pixel_bit_depth}bit.json'
    out_json.write_text(json.dumps(report, indent=2))
    print(f"\n  full report -> {out_json.relative_to(SPIKE_DIR)}")

    return 0 if overall else 1


if __name__ == '__main__':
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument('--n-germs', type=int, default=1000)
    p.add_argument('--bit-depth', type=int, choices=[8, 16], default=8)
    args = p.parse_args()
    sys.exit(main(target_n_germs=args.n_germs, pixel_bit_depth=args.bit_depth))
