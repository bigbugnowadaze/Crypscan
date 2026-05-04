"""Reed-Solomon byte-stream error correction layer for spike-2.

Layer placement (between Brotli compression and the AXP6 inner header
in the encode pipeline; symmetrically on the decode side):

    payload bytes
       -> Brotli compress
       -> RS(255, 223) chunked encode  <--- this layer
       -> AXP6 inner header (header.pack_header)
       -> bit-pack into 39-bit germ frames

RS(255, 223) is the canonical Reed-Solomon configuration over GF(2^8):
each 223-byte data block is augmented by 32 parity bytes for a total of
255 bytes per RS frame. It can correct up to 16 byte-flip errors per
frame (16 = (255-223)/2). The overhead is fixed at 32/223 = 14.35%.

For spike-2 the ECC absorbs single-byte flips that the 8-bit-pixel-depth
inverse fit may produce when a coefficient lands just over a quantization
boundary.
"""
from __future__ import annotations
from reedsolo import RSCodec

# Standard RS configuration: 255 total, 223 data, 32 parity per frame.
RS_TOTAL = 255
RS_DATA = 223
RS_PARITY = RS_TOTAL - RS_DATA   # 32

_codec = RSCodec(RS_PARITY)


def rs_encode(data: bytes) -> bytes:
    """Encode `data` into a stream of RS(255, 223) frames.

    Frames concatenated; final frame may have padding to fill the 223-byte
    data field — the padding length is encoded in a 4-byte little-endian
    prefix prepended to the output so the decoder can strip it precisely.
    """
    n = len(data)
    full = (n // RS_DATA) * RS_DATA
    remainder = n - full
    if remainder:
        # Pad final block with zeros up to RS_DATA
        pad_len = RS_DATA - remainder
        padded = data + bytes(pad_len)
    else:
        pad_len = 0
        padded = data

    n_frames = len(padded) // RS_DATA
    encoded = bytearray()
    for i in range(n_frames):
        block = padded[i * RS_DATA: (i + 1) * RS_DATA]
        frame = bytes(_codec.encode(block))
        encoded += frame

    # Prefix the original data length (4 bytes LE) so the decoder can
    # recover the exact byte count.
    prefix = n.to_bytes(4, 'little')
    return prefix + bytes(encoded)


def rs_decode(stream: bytes) -> tuple[bytes, dict]:
    """Decode an RS-encoded stream produced by `rs_encode`.

    Returns:
        original_data: bytes
        stats: dict with keys
            'n_frames'         total RS frames in stream
            'n_corrected'      number of frames that needed correction
            'corrected_bytes'  total byte errors corrected across frames
            'failed_frames'    indices of frames that failed to decode
    """
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
            # Push uncorrected data through (first 223 bytes) so caller
            # can still inspect; the SHA-256 check will fail upstream.
            decoded += frame[:RS_DATA]

    decoded = bytes(decoded[:n_original])
    return decoded, {
        'n_frames': n_frames,
        'n_corrected': n_corrected_frames,
        'corrected_bytes': corrected_bytes_total,
        'failed_frames': failed_frames,
    }
