"""Reed-Solomon ECC for spike-9B — RS(127, 111) instead of RS(255, 223).

Spike-9B's larger germs (σ=8 channel-matched scale) reduce the per-canvas
grid to ~169 slots (was ~676 in P3.A). After 16 pilots + 8 manifest, the
payload area is ~145 germs. RS(255, 223) outputs minimum 259 bytes per
chunk, which doesn't fit. RS(127, 111) outputs minimum 127 bytes per
chunk for the same ~14% parity overhead, which DOES fit.

For spike-9B's purposes (architectural existence proof, not density
parity with V2.1), this is a fine trade.
"""
from __future__ import annotations
from reedsolo import RSCodec

RS_TOTAL = 127
RS_DATA = 111
RS_PARITY = RS_TOTAL - RS_DATA   # 16

_codec = RSCodec(RS_PARITY, nsize=RS_TOTAL)


def rs_encode(data: bytes) -> bytes:
    """Encode `data` into a stream of RS(127, 111) frames.

    Output prefixed with a 4-byte little-endian uint32 holding the
    padding length (so decoder can strip exactly).
    """
    n = len(data)
    full = (n // RS_DATA) * RS_DATA
    pad = (RS_DATA - (n - full)) % RS_DATA
    padded = data + (b'\x00' * pad)
    encoded = bytes(_codec.encode(padded))
    return pad.to_bytes(4, 'little') + encoded


def rs_decode(data: bytes) -> tuple[bytes, dict]:
    """Decode RS-encoded byte stream. Returns (decoded_payload, stats)."""
    if len(data) < 4:
        raise ValueError(f"input too short: {len(data)} bytes (need >=4)")
    pad = int.from_bytes(data[:4], 'little')
    encoded = data[4:]
    if len(encoded) % RS_TOTAL != 0:
        raise ValueError(
            f"RS-encoded body length {len(encoded)} not a multiple of "
            f"frame size {RS_TOTAL}"
        )

    n_frames = len(encoded) // RS_TOTAL
    decoded_chunks: list[bytes] = []
    n_corrected = 0
    failed_frames: list[int] = []
    for i in range(n_frames):
        frame = encoded[i * RS_TOTAL:(i + 1) * RS_TOTAL]
        try:
            decoded, _, errata = _codec.decode(frame)
            decoded_chunks.append(bytes(decoded))
            if len(errata) > 0:
                n_corrected += 1
        except Exception:
            failed_frames.append(i)
            decoded_chunks.append(frame[:RS_DATA])

    decoded = b''.join(decoded_chunks)
    if pad:
        decoded = decoded[:-pad] if pad <= len(decoded) else decoded
    stats = {'n_frames': n_frames, 'n_corrected': n_corrected,
              'failed_frames': failed_frames}
    return decoded, stats
