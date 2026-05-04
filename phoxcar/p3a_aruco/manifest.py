"""Manifest cluster — replaces the JSON sidecar.

Encodes the carrier-specific parameters that the decoder needs after pose
recovery, but before payload decode:

    bytes 0..3  : magic 'PHX1'  (sanity check)
    bytes 4..7  : payload byte count (uint32 LE)

Total: 8 bytes = 8 manifest germs (1 byte/germ via codebook).

Encoded at canonical positions just inside the NW finder corner. Decoder
samples them after rectification and recovers the manifest fields.
"""
from __future__ import annotations
import struct
import numpy as np


MANIFEST_MAGIC = b'PHX1'
MANIFEST_BYTE_COUNT = 8                     # 4 magic + 4 payload-size
MANIFEST_GERM_COUNT = MANIFEST_BYTE_COUNT   # 1 byte/germ


def encode_manifest_bytes(payload_byte_count: int) -> bytes:
    if payload_byte_count > 0xFFFFFFFF:
        raise ValueError(f"payload too large: {payload_byte_count}")
    return MANIFEST_MAGIC + struct.pack('<I', payload_byte_count)


def parse_manifest_bytes(data: bytes) -> int:
    if len(data) < MANIFEST_BYTE_COUNT:
        raise ValueError(f"manifest too short: {len(data)} bytes")
    if data[:4] != MANIFEST_MAGIC:
        raise ValueError(f"manifest magic mismatch: got {data[:4].hex()}")
    return struct.unpack('<I', data[4:8])[0]


def canonical_manifest_positions(
    nw_finder_pos: tuple[int, int],
    spacing: int,
    n_germs: int = MANIFEST_GERM_COUNT,
) -> list[tuple[int, int]]:
    """Manifest germs sit in a horizontal row just inside the NW finder.

    Specifically, at (nw_x + spacing, nw_y), (nw_x + 2*spacing, nw_y), ...
    so the manifest is laid out along the top edge of the carrier interior.
    """
    nx, ny = nw_finder_pos
    return [(nx + (i + 1) * spacing, ny) for i in range(n_germs)]
