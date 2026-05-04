"""Reed-Solomon RS(255, 191) byte-stream ECC for spike-5.

Stronger than spike-3/spike-4's RS(255, 223): corrects up to 32 byte
errors per 255-byte frame (12.5% byte-error tolerance) at 33.5% size
overhead (vs spike-3's 16 errors / 6.3% / 14.3% overhead).

Combined with R=3 per-germ replication + byte-level majority vote (see
redundancy.py), this is the spike-5 mitigation stack for the spike-4
finding that the substrate at R=1 / RS(255, 223) was zero-margin under
photometric noise.
"""
from __future__ import annotations
from reedsolo import RSCodec

RS_TOTAL = 255
RS_DATA = 191
RS_PARITY = RS_TOTAL - RS_DATA   # 64

_codec = RSCodec(RS_PARITY)


def rs_encode(data: bytes) -> bytes:
    """Encode `data` into RS(255, 191) frames with a 4-byte length prefix."""
    n = len(data)
    full = (n // RS_DATA) * RS_DATA
    remainder = n - full
    if remainder:
        pad_len = RS_DATA - remainder
        padded = data + bytes(pad_len)
    else:
        padded = data
    n_frames = len(padded) // RS_DATA
    encoded = bytearray()
    for i in range(n_frames):
        block = padded[i * RS_DATA: (i + 1) * RS_DATA]
        encoded += bytes(_codec.encode(block))
    prefix = n.to_bytes(4, 'little')
    return prefix + bytes(encoded)


def rs_decode(stream: bytes) -> tuple[bytes, dict]:
    """Decode an RS(255, 191) stream produced by `rs_encode`."""
    if len(stream) < 4:
        raise ValueError("RS stream too short to contain length prefix")
    n_original = int.from_bytes(stream[:4], 'little')
    body = stream[4:]
    if len(body) % RS_TOTAL != 0:
        raise ValueError(
            f"RS body length {len(body)} is not a multiple of {RS_TOTAL}"
        )
    n_frames = len(body) // RS_TOTAL
    decoded = bytearray()
    n_corrected_frames = 0
    corrected_bytes_total = 0
    failed_frames = []
    for i in range(n_frames):
        frame = body[i * RS_TOTAL: (i + 1) * RS_TOTAL]
        try:
            data, _, errata = _codec.decode(frame)
            data = bytes(data)
            decoded += data
            n_err = len(errata)
            if n_err > 0:
                n_corrected_frames += 1
                corrected_bytes_total += n_err
        except Exception:
            failed_frames.append(i)
            decoded += frame[:RS_DATA]
    decoded = bytes(decoded[:n_original])
    return decoded, {
        'n_frames': n_frames,
        'n_corrected': n_corrected_frames,
        'corrected_bytes': corrected_bytes_total,
        'failed_frames': failed_frames,
    }
