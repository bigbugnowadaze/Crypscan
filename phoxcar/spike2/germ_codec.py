"""5-coefficient germ <-> bytes codec in the orthonormal basis.

Differences from spike-1's codec:

1. Quantization is in c_ortho coordinates (not raw theta). The
   orthonormal basis decouples noise per coefficient — independent
   8-bit quantization in c_ortho corresponds to coupled-but-bounded
   noise in raw theta, which is what the inverse solver actually
   recovers cleanly.

2. The H^2 forward model loses the sign of the whole theta vector. To
   restore it without re-introducing the bit, the codec enforces the
   convention `c_ortho[0] >= 0`. The encoder negates the whole
   c_ortho vector if the input would otherwise produce c_ortho[0] < 0.
   The decoder enforces the same convention on the recovered fit.

3. The convention costs effectively 1 bit per germ: half the
   8-bits-per-coef (256-level) bytespace for c_ortho[0] is
   never produced by the encoder (the negative-c_ortho[0] half).
   We use a 7-bit quantization for c_ortho[0] (range [0, +bound_0]
   over 128 levels) and 8-bit quantization for c_ortho[1..4] (range
   [-bound_j, +bound_j] over 256 levels).

   Total bits per germ: 7 + 4*8 = 39. Spike-1 used 40, so spike-2 has
   a 2.5% density penalty in exchange for sign disambiguation.

# Bit packing

39 bits per germ, packed into 5 bytes:

    byte 0: bit 7 = 0 (reserved; canonical sign-bit slot, always 0)
    byte 0: bits 0-6 = c_ortho[0] index in [0, 127]
    byte 1: c_ortho[1] index in [0, 255]
    byte 2: c_ortho[2] index in [0, 255]
    byte 3: c_ortho[3] index in [0, 255]
    byte 4: c_ortho[4] index in [0, 255]

The upstream byte stream is bit-packed into this 39-bits-per-germ
layout. See `bit_pack_payload_to_germ_bytes()` and `bit_unpack_germ_bytes_to_payload()`.
"""
from __future__ import annotations
import numpy as np

LEVELS_C0 = 128
LEVELS_OTHER = 256


def quant_step_c0(bound_0: float) -> float:
    return bound_0 / (LEVELS_C0 - 1)


def quant_step_other(bound_j: float) -> float:
    return (2.0 * bound_j) / (LEVELS_OTHER - 1)


def _quantize_c0(value: float, bound: float) -> int:
    v = max(0.0, min(bound, float(value)))
    q = int(round(v * (LEVELS_C0 - 1) / bound))
    return max(0, min(LEVELS_C0 - 1, q))


def _dequantize_c0(q: int, bound: float) -> float:
    return (q / (LEVELS_C0 - 1)) * bound


def _quantize_other(value: float, bound: float) -> int:
    v = max(-bound, min(bound, float(value)))
    q = int(round((v + bound) * (LEVELS_OTHER - 1) / (2.0 * bound)))
    return max(0, min(LEVELS_OTHER - 1, q))


def _dequantize_other(q: int, bound: float) -> float:
    return (q / (LEVELS_OTHER - 1)) * (2.0 * bound) - bound


# ---------------------------------------------------------------------------
# Sign canonicalization
# ---------------------------------------------------------------------------

def canonicalize_sign(c_ortho: np.ndarray) -> tuple[np.ndarray, bool]:
    """Apply sign convention `c_ortho[0] >= 0`.

    Returns:
        c_canon: (5,) canonical c_ortho.
        was_flipped: True if the input had c_ortho[0] < 0 and we negated.
    """
    if c_ortho[0] < 0:
        return -c_ortho, True
    return c_ortho.copy(), False


# ---------------------------------------------------------------------------
# c_ortho <-> 5 bytes
# ---------------------------------------------------------------------------

def c_ortho_to_bytes(c_ortho: np.ndarray, bounds: np.ndarray) -> bytes:
    """Quantize one canonicalized c_ortho (with c_ortho[0] >= 0) to 5 bytes
    using the basis's per-coefficient codebook bounds."""
    if c_ortho[0] < 0:
        raise ValueError("c_ortho[0] must be non-negative — call canonicalize_sign first")
    q0 = _quantize_c0(c_ortho[0], bounds[0])
    out = bytearray(5)
    out[0] = q0 & 0x7F                                         # bit 7 = 0
    for j in range(1, 5):
        out[j] = _quantize_other(c_ortho[j], bounds[j])
    return bytes(out)


def bytes_to_c_ortho(data: bytes, bounds: np.ndarray) -> np.ndarray:
    """Dequantize 5 bytes to c_ortho (5,) using basis bounds. c_ortho[0] >= 0."""
    if len(data) != 5:
        raise ValueError(f"expected 5 bytes, got {len(data)}")
    if data[0] & 0x80:
        raise ValueError(f"byte 0 MSB must be 0 (got byte 0 = 0x{data[0]:02x})")
    c = np.zeros(5, dtype=np.float64)
    c[0] = _dequantize_c0(data[0] & 0x7F, bounds[0])
    for j in range(1, 5):
        c[j] = _dequantize_other(data[j], bounds[j])
    return c


# ---------------------------------------------------------------------------
# Bit packing: payload bytes <-> germ bytes (39 bits per germ)
# ---------------------------------------------------------------------------

BITS_PER_GERM = 39

def bit_pack_payload_to_germ_bytes(payload: bytes) -> tuple[bytes, int]:
    """Pack a payload byte stream into 5-bytes-per-germ form.

    The first 7 bits of every 39-bit germ go into byte 0 bits 0-6
    (with byte 0 bit 7 = 0). The remaining 32 bits go into bytes 1-4.

    Returns:
        germ_bytes: 5 * n_germs bytes.
        n_germs: total germs needed to carry the payload.
    """
    total_bits = len(payload) * 8
    n_germs = (total_bits + BITS_PER_GERM - 1) // BITS_PER_GERM

    # Read bits MSB-first from the payload.
    out = bytearray(5 * n_germs)
    bit_pos = 0
    for g in range(n_germs):
        # Pull 39 bits starting at bit_pos.
        bits = []
        for k in range(BITS_PER_GERM):
            i = bit_pos + k
            if i < total_bits:
                bits.append((payload[i >> 3] >> (7 - (i & 7))) & 1)
            else:
                bits.append(0)                  # zero-pad final germ
        bit_pos += BITS_PER_GERM
        # Layout: first 7 bits -> byte 0 bits 0-6, then 8 bits each into bytes 1-4.
        # Within each byte, MSB-first.
        b0 = 0
        for k in range(7):
            b0 = (b0 << 1) | bits[k]
        out[5 * g] = b0                         # byte 0 bit 7 = 0 by construction
        for j in range(4):
            v = 0
            for k in range(8):
                v = (v << 1) | bits[7 + j * 8 + k]
            out[5 * g + 1 + j] = v
    return bytes(out), n_germs


def bit_unpack_germ_bytes_to_payload(germ_bytes: bytes, n_payload_bytes: int) -> bytes:
    """Inverse of bit_pack_payload_to_germ_bytes.

    Reads `n_germs = len(germ_bytes) // 5` germs and produces a payload
    of exactly `n_payload_bytes` bytes (truncating zero-padding from the
    final germ).
    """
    if len(germ_bytes) % 5 != 0:
        raise ValueError(f"germ_bytes length {len(germ_bytes)} is not a multiple of 5")
    n_germs = len(germ_bytes) // 5

    bits = []
    for g in range(n_germs):
        b0 = germ_bytes[5 * g]
        if b0 & 0x80:
            raise ValueError(f"germ {g} byte 0 MSB must be 0; got 0x{b0:02x}")
        for k in range(7):
            bits.append((b0 >> (6 - k)) & 1)
        for j in range(4):
            v = germ_bytes[5 * g + 1 + j]
            for k in range(8):
                bits.append((v >> (7 - k)) & 1)

    # Pack `bits` into `n_payload_bytes` bytes (MSB-first within each byte).
    if len(bits) < n_payload_bytes * 8:
        raise ValueError(
            f"not enough bits for {n_payload_bytes} payload bytes: have {len(bits)}"
        )
    out = bytearray(n_payload_bytes)
    for i in range(n_payload_bytes * 8):
        if bits[i]:
            out[i >> 3] |= 1 << (7 - (i & 7))
    return bytes(out)
