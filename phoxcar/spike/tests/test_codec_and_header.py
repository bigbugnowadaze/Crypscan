"""Unit tests for header.py and germ_codec.py.

Independent of render/extract — these fail fast if the symbol-packing or
header layout has a bug, before paying the full roundtrip cost.
"""
from __future__ import annotations
import hashlib
import sys
from pathlib import Path

import numpy as np

SPIKE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SPIKE_DIR))

from header import pack_header, parse_header, MAGIC, VERSION                    # noqa: E402
from germ_codec import (                                                         # noqa: E402
    bytes_to_germs, germs_to_bytes, n_germs_for_bytes, pad_bytes_to_germ_boundary,
    quantize_then_dequantize, COEF_BOUNDS, BYTES_PER_GERM, QUANT_STEP,
    quantize_one, dequantize_one,
)


def test_header_roundtrip():
    payload = b"hello phoxcar world" * 17
    compressed = b"\x9a\x12\x34" + payload[::-1]
    framed = pack_header(payload, compressed, "test.bin")
    parsed = parse_header(framed)
    assert parsed['magic'] == MAGIC
    assert parsed['version'] == VERSION
    assert parsed['comp_method'] == 1
    assert parsed['original_size'] == len(payload)
    assert parsed['compressed_len'] == len(compressed)
    assert parsed['expected_hash'] == hashlib.sha256(payload).digest()
    assert parsed['filename'] == 'test.bin'
    assert parsed['compressed_payload'] == compressed
    print("  test_header_roundtrip OK")


def test_quantize_one_extremes():
    for j, bound in enumerate(COEF_BOUNDS):
        assert quantize_one(-bound, bound) == 0
        assert quantize_one(+bound, bound) == 255
        # Mid-range
        q = quantize_one(0.0, bound)
        # Linear quantization with 256 levels: 0 maps to ~127 or 128
        assert q in (127, 128)
        # Round-trip stability inside the codebook
        for k in range(256):
            v = dequantize_one(k, bound)
            assert quantize_one(v, bound) == k, f"unstable at k={k}, bound={bound}"
    print("  test_quantize_one_extremes OK")


def test_germs_bytes_roundtrip():
    # Random germs in the codebook (snapped to grid).
    rng = np.random.default_rng(seed=1234)
    n = 137
    germs = (rng.uniform(-1, 1, size=(n, 5))) * COEF_BOUNDS[None, :]
    germs_q = quantize_then_dequantize(germs)
    raw = germs_to_bytes(germs_q)
    germs_back = bytes_to_germs(raw, n)
    np.testing.assert_array_equal(germs_q, germs_back)
    print("  test_germs_bytes_roundtrip OK")


def test_arbitrary_bytes_roundtrip():
    # Critically: any byte stream must survive the bytes -> germs -> bytes
    # roundtrip after padding to germ boundary.
    rng = np.random.default_rng(seed=5678)
    for n_bytes in [1, 4, 5, 6, 50, 1000, 4007]:
        raw = bytes(rng.integers(0, 256, n_bytes).tolist())
        padded = pad_bytes_to_germ_boundary(raw)
        n_germs = len(padded) // BYTES_PER_GERM
        germs = bytes_to_germs(padded, n_germs)
        # Quantize-then-dequantize should be a no-op since each byte already
        # represents an 8-bit quantization index.
        germs_q = quantize_then_dequantize(germs)
        raw_back = germs_to_bytes(germs_q)
        # The first n_bytes must be identical; padding is zeroes.
        assert raw_back[:n_bytes] == raw, f"bytes roundtrip failed at n_bytes={n_bytes}"
        assert raw_back[n_bytes:] == bytes(len(padded) - n_bytes)
    print("  test_arbitrary_bytes_roundtrip OK")


def test_n_germs_for_bytes():
    assert n_germs_for_bytes(0) == 0
    assert n_germs_for_bytes(1) == 1
    assert n_germs_for_bytes(5) == 1
    assert n_germs_for_bytes(6) == 2
    assert n_germs_for_bytes(10) == 2
    assert n_germs_for_bytes(11) == 3
    print("  test_n_germs_for_bytes OK")


def test_quant_step_matches_bounds():
    # QUANT_STEP[j] = 2 * bound[j] / 255
    for j in range(5):
        expected = 2.0 * COEF_BOUNDS[j] / 255.0
        assert abs(QUANT_STEP[j] - expected) < 1e-12
    print("  test_quant_step_matches_bounds OK")


if __name__ == '__main__':
    print("running unit tests for header.py and germ_codec.py ...")
    test_header_roundtrip()
    test_quantize_one_extremes()
    test_germs_bytes_roundtrip()
    test_arbitrary_bytes_roundtrip()
    test_n_germs_for_bytes()
    test_quant_step_matches_bounds()
    print("ALL UNIT TESTS PASSED")
