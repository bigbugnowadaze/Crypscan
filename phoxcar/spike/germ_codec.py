"""5-coefficient germ <-> bytes codec.

Per `03_PHOXOIDAL_CARRIER_ARCHITECTURE.md` section 6 (default option) and
`05_INFORMATION_DENSITY_ANALYSIS.md` section 2.1: 8 bits per coefficient
times 5 coefficients = 40 bits per germ.

# Spike-specific simplification

Production bounds from CRYPSOID's tools/crypsorender/math/germ.py
lines 162-166 are MAX_KAPPA=25, MAX_CHI_OMEGA=50, MAX_ZETA=100. The
spike uses *unit bounds* (all coefficients in [-1, +1]) so the
renderer's intensity profile stays in a numerically clean regime
without the per-coefficient amplitude balancing that the production
substrate would need. The 8-bits-per-coefficient budget is identical;
only the dequantized magnitudes differ.

The Phase 1 production substrate must restore CRYPSOID's bounds and
solve the per-coefficient amplitude / SNR question in `09_OPEN_QUESTIONS.md`
section 6 and `06_DECODER_RESEARCH_PLAN.md` section 4.5.

# Bit layout per germ (big-endian within the germ)

    byte 0 : kappa1 quantized to 8 bits over [-bound, +bound]
    byte 1 : kappa2
    byte 2 : chi
    byte 3 : omega
    byte 4 : zeta
"""
from __future__ import annotations
import numpy as np

# ---------------------------------------------------------------------------
# Production bounds (cite for documentation; not used by the spike itself).
# ---------------------------------------------------------------------------
PROD_MAX_KAPPA = 25.0
PROD_MAX_CHI_OMEGA = 50.0
PROD_MAX_ZETA = 100.0
PROD_COEF_BOUNDS = np.array([
    PROD_MAX_KAPPA, PROD_MAX_KAPPA,
    PROD_MAX_CHI_OMEGA, PROD_MAX_CHI_OMEGA,
    PROD_MAX_ZETA,
], dtype=np.float64)

# ---------------------------------------------------------------------------
# Spike bounds (used by the spike encoder / renderer / decoder).
# ---------------------------------------------------------------------------
COEF_BOUNDS = np.array([1.0, 1.0, 1.0, 1.0, 1.0], dtype=np.float64)

BITS_PER_COEF = 8
COEFS_PER_GERM = 5
BITS_PER_GERM = BITS_PER_COEF * COEFS_PER_GERM   # 40
BYTES_PER_GERM = BITS_PER_GERM // 8              # 5

QUANT_LEVELS = 1 << BITS_PER_COEF                 # 256
QUANT_STEP = (2.0 * COEF_BOUNDS) / (QUANT_LEVELS - 1)


def quantize_one(value: float, bound: float) -> int:
    """Map value in [-bound, +bound] to an int in [0, 255]."""
    v = max(-bound, min(bound, float(value)))
    q = int(round((v + bound) * (QUANT_LEVELS - 1) / (2.0 * bound)))
    return max(0, min(QUANT_LEVELS - 1, q))


def dequantize_one(q: int, bound: float) -> float:
    """Inverse of quantize_one."""
    return (q / (QUANT_LEVELS - 1)) * (2.0 * bound) - bound


def germs_to_bytes(germs: np.ndarray) -> bytes:
    """(N, 5) float -> bytes of length N*5."""
    germs = np.asarray(germs, dtype=np.float64)
    if germs.ndim != 2 or germs.shape[1] != COEFS_PER_GERM:
        raise ValueError(f"germs must be (N, 5), got {germs.shape}")
    n = germs.shape[0]
    out = bytearray(n * BYTES_PER_GERM)
    for i in range(n):
        for j in range(COEFS_PER_GERM):
            out[i * BYTES_PER_GERM + j] = quantize_one(germs[i, j], COEF_BOUNDS[j])
    return bytes(out)


def bytes_to_germs(data: bytes, n_germs: int) -> np.ndarray:
    """Inverse of germs_to_bytes. Returns (N, 5) float64."""
    if len(data) < n_germs * BYTES_PER_GERM:
        raise ValueError(
            f"data too short: got {len(data)} bytes, need {n_germs * BYTES_PER_GERM}"
        )
    germs = np.zeros((n_germs, COEFS_PER_GERM), dtype=np.float64)
    for i in range(n_germs):
        for j in range(COEFS_PER_GERM):
            q = data[i * BYTES_PER_GERM + j]
            germs[i, j] = dequantize_one(q, COEF_BOUNDS[j])
    return germs


def n_germs_for_bytes(n_bytes: int) -> int:
    """How many germs are required to carry n_bytes (rounded up)."""
    return (n_bytes + BYTES_PER_GERM - 1) // BYTES_PER_GERM


def pad_bytes_to_germ_boundary(data: bytes) -> bytes:
    """Pad bytes with zero to a multiple of BYTES_PER_GERM."""
    rem = len(data) % BYTES_PER_GERM
    if rem == 0:
        return data
    return data + bytes(BYTES_PER_GERM - rem)


def quantize_then_dequantize(germs: np.ndarray) -> np.ndarray:
    """Round-trip a germ matrix through the quantization grid (encoder reference)."""
    return bytes_to_germs(germs_to_bytes(germs), germs.shape[0])
