"""5-coefficient germ codec for spike-3.

Differences from spike-2:

  - No sign convention (the sigmoid forward model is sign-preserving).
  - Full 8 bits per coefficient on every coefficient: 40 bits per germ.
  - Byte-aligned: 5 bytes per germ exactly. No fractional bit packing.

The codec quantizes in c_ortho coordinates (orthonormal basis) for
per-coefficient noise decoupling. Codebook bounds come from the basis
(`OrthoBasis.codebook_bounds`) and are sized so all byte patterns map
to theta_raw in the unit cube.
"""
from __future__ import annotations
import numpy as np

LEVELS = 256


def quant_step(bound: float) -> float:
    return (2.0 * bound) / (LEVELS - 1)


def _quantize(value: float, bound: float) -> int:
    v = max(-bound, min(bound, float(value)))
    q = int(round((v + bound) * (LEVELS - 1) / (2.0 * bound)))
    return max(0, min(LEVELS - 1, q))


def _dequantize(q: int, bound: float) -> float:
    return (q / (LEVELS - 1)) * (2.0 * bound) - bound


def c_ortho_to_bytes(c_ortho: np.ndarray, bounds: np.ndarray) -> bytes:
    """Quantize a c_ortho 5-vector to 5 bytes."""
    out = bytearray(5)
    for j in range(5):
        out[j] = _quantize(c_ortho[j], bounds[j])
    return bytes(out)


def bytes_to_c_ortho(data: bytes, bounds: np.ndarray) -> np.ndarray:
    """Dequantize 5 bytes to a c_ortho 5-vector."""
    if len(data) != 5:
        raise ValueError(f"expected 5 bytes, got {len(data)}")
    c = np.zeros(5, dtype=np.float64)
    for j in range(5):
        c[j] = _dequantize(data[j], bounds[j])
    return c


def n_germs_for_bytes(n_bytes: int) -> int:
    """How many 5-byte germs are needed to carry n_bytes (rounded up)."""
    return (n_bytes + 4) // 5


def pad_bytes_to_germ_boundary(data: bytes) -> bytes:
    """Pad bytes with zero to a multiple of 5 (one germ = 5 bytes)."""
    rem = len(data) % 5
    if rem == 0:
        return data
    return data + bytes(5 - rem)
