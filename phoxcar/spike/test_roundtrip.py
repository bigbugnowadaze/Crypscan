"""Phoxcar spike acceptance gate.

Runs the full encode -> render -> extract -> decode pathway on a synthetic
~1000-germ payload and asserts:

    1. SHA-256 of decoded == SHA-256 of input  (the GATE)
    2. Per-coefficient RMSE between encoder's quantized germs and decoder's
       recovered germs <= quantization step.
    3. Total wall time < 30 seconds.

Output: results/roundtrip_<timestamp>.txt with full metrics.

Per the README's "Decision rule for the spike":
    GATE PASS  + RMSE <= step    -> Phase 1 P3 architecturally justified.
    GATE PASS  + RMSE > step     -> tighten extract; re-run before Phase 1.
    GATE FAIL                     -> re-open v4-vs-v3 decision.
"""
from __future__ import annotations
import hashlib
import json
import sys
import time
from datetime import datetime
from pathlib import Path

import numpy as np

# Make the spike directory importable regardless of cwd
SPIKE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SPIKE_DIR))

from encoder import encode, EncodeParams           # noqa: E402
from decoder import decode_with_manifest           # noqa: E402
from germ_codec import (                            # noqa: E402
    bytes_to_germs, germs_to_bytes, pad_bytes_to_germ_boundary,
    quantize_then_dequantize, BYTES_PER_GERM, COEF_BOUNDS, QUANT_STEP,
)
from header import pack_header                      # noqa: E402
import brotli                                       # noqa: E402


# ------------------------------------------------------------------
# Test payload: structured text that compresses well via Brotli, big enough
# to require ~1000 germs after compression+header.
# ------------------------------------------------------------------

def make_payload(target_n_germs: int) -> bytes:
    """Build a payload whose compressed+framed size targets ~target_n_germs germs.

    Compression ratio for varied dictionary text (post-Brotli q=11) is ~0.20,
    so for target_n_germs * 5 bytes of compressed payload we need
    target_n_germs * 5 / 0.20 = target_n_germs * 25 bytes of source text.
    """
    base = (
        "Phoxoidal carrier spike payload — Phase 0.5 acceptance gate.\n"
        "If this text decodes byte-exact via SHA-256 verification, the symbol\n"
        "encoding pathway through 5-coefficient germs is mathematically\n"
        "tractable at zero capture noise. That is necessary for Phase 1 P3\n"
        "(decoder branch) to be architecturally justified, but not sufficient.\n"
        "Capture-mediated robustness is a separate Phase 1 deliverable.\n"
    )
    rng = np.random.default_rng(seed=20260503)
    words = base.split()
    # Aim for source size ~ 25 * target_n_germs bytes; mean word len ~6 + space.
    n_pad_words = (target_n_germs * 25) // 7
    pad_words = [words[i % len(words)] for i in rng.integers(0, len(words), n_pad_words)]
    return (base + ' '.join(pad_words)).encode('utf-8')


def main(target_n_germs: int = 1000, pixel_bit_depth: int = 16) -> int:
    t0 = time.perf_counter()

    print("=" * 70)
    print(f"  phoxcar spike — acceptance gate (pixel_bit_depth={pixel_bit_depth})")
    print("=" * 70)

    # 1. Build a payload sized so the encoder needs ~ target_n_germs germs.
    #    Compression ratio ~0.4 for varied text; tune by trial below.
    payload = make_payload(target_n_germs)

    # Quick sanity: see what compressed + framed size we get; if far from
    # target, scale the payload.
    compressed = brotli.compress(payload, quality=11)
    framed_len = 48 + len("payload.txt") + len(compressed)   # AXP6 header layout
    n_germs_est = (framed_len + BYTES_PER_GERM - 1) // BYTES_PER_GERM
    print(f"  payload bytes        : {len(payload):,}")
    print(f"  compressed bytes     : {len(compressed):,}")
    print(f"  framed + padded est. : {framed_len:,}")
    print(f"  germs needed (est.)  : {n_germs_est:,}")

    # 2. Compute the expected SHA-256 (the gate's truth).
    expected_sha = hashlib.sha256(payload).digest()
    print(f"  expected sha256      : {expected_sha.hex()[:32]}...")

    # 3. Encode.
    out_png = SPIKE_DIR / 'results' / f'spike_carrier_{pixel_bit_depth}bit.png'
    out_png.parent.mkdir(parents=True, exist_ok=True)
    params = EncodeParams(pixel_bit_depth=pixel_bit_depth)
    print()
    print("  ENCODING ...")
    t_enc0 = time.perf_counter()
    enc_manifest = encode(payload, "payload.txt", out_png, params=params, sidecar=True)
    t_enc = time.perf_counter() - t_enc0
    print(f"    PNG dimensions     : {enc_manifest['width']} x {enc_manifest['height']}")
    print(f"    PNG bytes on disk  : {enc_manifest['png_bytes']:,}")
    print(f"    germs in carrier   : {enc_manifest['n_germs']:,}")
    print(f"    encode wall time   : {t_enc:.2f}s")

    # 4. Decode.
    sidecar = out_png.with_suffix(out_png.suffix + '.manifest.json')
    print()
    print("  DECODING ...")
    t_dec0 = time.perf_counter()
    res = decode_with_manifest(out_png, sidecar)
    t_dec = time.perf_counter() - t_dec0
    print(f"    sha256 ok          : {res.sha256_ok}")
    print(f"    size ok            : {res.size_ok}")
    print(f"    actual sha256      : {res.sha256.hex()[:32]}...")
    print(f"    extract residual   : max={res.extract_residual_max:.6f}, "
          f"mean={res.extract_residual_mean:.6f}")
    print(f"    decode wall time   : {t_dec:.2f}s")

    # 5. Per-coefficient RMSE: re-derive what the encoder shipped as germs and
    #    compare to what the decoder recovered.
    framed = pack_header(payload, compressed, "payload.txt")
    padded = pad_bytes_to_germ_boundary(framed)
    n_germs = len(padded) // BYTES_PER_GERM
    enc_germs = quantize_then_dequantize(bytes_to_germs(padded, n_germs))

    # Decoder germs must be re-fetched from the manifest+carrier path. Since
    # `decode_with_manifest` doesn't return the germs directly, re-run the
    # extract here for the comparison. (Adding a return value to the decoder
    # would break a clean API; the test doing it inline is fine.)
    from extract import extract_carrier                    # noqa: E402
    from PIL import Image                                  # noqa: E402
    img = Image.open(out_png)
    arr = np.asarray(img)
    if img.mode == 'L':
        carrier = arr.astype(np.float32) / 255.0
    elif img.mode in ('I;16', 'I'):
        carrier = arr.astype(np.float32) / 65535.0
    else:
        carrier = np.asarray(img.convert('L'), dtype=np.float32) / 255.0
    positions = np.array(enc_manifest['positions'], dtype=np.int64)
    dec_germs, _ = extract_carrier(
        carrier, positions,
        sigma=params.sigma, half_size=params.half_size,
        amp=params.amp, baseline=params.baseline,
    )

    diff = dec_germs - enc_germs
    per_coef_rmse = np.sqrt(np.mean(diff * diff, axis=0))
    per_coef_max = np.max(np.abs(diff), axis=0)
    print()
    print("  PER-COEFFICIENT RECOVERY")
    print(f"    coef         RMSE         max-abs      quant-step    rmse <= step?")
    coef_names = ['kappa1', 'kappa2', 'chi   ', 'omega ', 'zeta  ']
    rmse_ok = True
    for j, name in enumerate(coef_names):
        ok = per_coef_rmse[j] <= QUANT_STEP[j]
        rmse_ok = rmse_ok and ok
        print(f"    {name}     {per_coef_rmse[j]:.6f}    {per_coef_max[j]:.6f}    "
              f"{QUANT_STEP[j]:.6f}    {'OK' if ok else 'FAIL'}")

    # 6. Acceptance gate.
    total_time = time.perf_counter() - t0
    print()
    print("=" * 70)
    sha_ok = res.sha256_ok and (res.sha256 == expected_sha)
    print(f"  GATE 1 — SHA-256 roundtrip                : "
          f"{'PASS' if sha_ok else 'FAIL'}")
    print(f"  GATE 2 — per-coef RMSE <= quant step      : "
          f"{'PASS' if rmse_ok else 'FAIL'}")
    print(f"  GATE 3 — total wall time < 30 s           : "
          f"{'PASS' if total_time < 30 else 'FAIL'}  ({total_time:.2f}s)")
    print()
    overall = sha_ok and rmse_ok and total_time < 30
    print(f"  OVERALL                                  : "
          f"{'PASS — Phase 1 P3 justified' if overall else 'FAIL — investigate'}")
    print("=" * 70)

    # 7. Persist a results report.
    timestamp = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    report = {
        'timestamp': timestamp,
        'spike_version': '0.1',
        'payload_size': len(payload),
        'compressed_size': len(compressed),
        'n_germs': enc_manifest['n_germs'],
        'png_dimensions': [enc_manifest['width'], enc_manifest['height']],
        'png_bytes': enc_manifest['png_bytes'],
        'expected_sha256': expected_sha.hex(),
        'actual_sha256': res.sha256.hex(),
        'sha256_ok': bool(sha_ok),
        'size_ok': bool(res.size_ok),
        'extract_residual_max': float(res.extract_residual_max),
        'extract_residual_mean': float(res.extract_residual_mean),
        'per_coef_rmse': per_coef_rmse.tolist(),
        'per_coef_max_abs': per_coef_max.tolist(),
        'quant_step': QUANT_STEP.tolist(),
        'rmse_ok': bool(rmse_ok),
        'wall_time_total_s': float(total_time),
        'wall_time_encode_s': float(t_enc),
        'wall_time_decode_s': float(t_dec),
        'gate_pass': bool(overall),
        'params': params.to_dict(),
    }
    out_json = SPIKE_DIR / 'results' / f'roundtrip_{timestamp}_{pixel_bit_depth}bit.json'
    out_json.write_text(json.dumps(report, indent=2))
    print(f"\n  full report -> {out_json.relative_to(SPIKE_DIR)}")

    return 0 if overall else 1


if __name__ == '__main__':
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument('--n-germs', type=int, default=1000)
    p.add_argument('--bit-depth', type=int, choices=[8, 16], default=16)
    args = p.parse_args()
    sys.exit(main(target_n_germs=args.n_germs, pixel_bit_depth=args.bit_depth))
