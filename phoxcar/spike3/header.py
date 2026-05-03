"""AXP6-equivalent inner header for the phoxoidal-carrier spike.

Bit-for-bit compatible with the inner-header layout in
aurexis_decode.py lines 535-548 (the bytes that sit inside the
compressed payload of an AXP6 carrier, NOT the manifest in the PNG
modules). Preserved verbatim per `03_PHOXOIDAL_CARRIER_ARCHITECTURE.md`
section 5: Brotli + SHA-256 + bit-exact carry forward unchanged.
"""
from __future__ import annotations
import hashlib
import struct

MAGIC = b'AXP6'
VERSION = 7
COMP_BROTLI = 1
HEADER_FIXED = 48  # bytes before the variable-length filename


def pack_header(
    original_payload: bytes,
    compressed_payload: bytes,
    filename: str,
) -> bytes:
    """Build the AXP6 inner header followed by the compressed payload bytes.

    Layout (matches aurexis_decode.py lines 535-548):
        offset 0   : 4 bytes  magic 'AXP6'
        offset 4   : 1 byte   version (7)
        offset 5   : 1 byte   comp_method (1 = brotli)
        offset 6   : 4 bytes  original_size (uint32 LE)
        offset 10  : 4 bytes  compressed_len (uint32 LE)
        offset 14  : 32 bytes expected_hash (SHA-256 of original_payload)
        offset 46  : 2 bytes  filename_len (uint16 LE)
        offset 48  : N bytes  filename (UTF-8)
        offset 48+N: compressed_len bytes  compressed_payload
    """
    fname_bytes = filename.encode('utf-8')
    if len(fname_bytes) > 0xFFFF:
        raise ValueError("filename too long (uint16 LE)")
    sha = hashlib.sha256(original_payload).digest()
    return (
        MAGIC
        + bytes([VERSION, COMP_BROTLI])
        + struct.pack('<I', len(original_payload))
        + struct.pack('<I', len(compressed_payload))
        + sha
        + struct.pack('<H', len(fname_bytes))
        + fname_bytes
        + compressed_payload
    )


def parse_header(header_plus_payload: bytes) -> dict:
    """Parse the AXP6 inner header and the compressed-payload tail.

    Returns:
        dict with keys: magic, version, comp_method, original_size,
        compressed_len, expected_hash, filename, compressed_payload
    """
    if len(header_plus_payload) < HEADER_FIXED:
        raise ValueError(f"too short for AXP6 header ({len(header_plus_payload)} < {HEADER_FIXED})")
    magic = header_plus_payload[:4]
    if magic != MAGIC:
        raise ValueError(f"not an AXP6 inner header (magic: {magic.hex()})")
    version = header_plus_payload[4]
    if version != VERSION:
        raise ValueError(f"unsupported version {version} (expected {VERSION})")
    comp_method = header_plus_payload[5]
    original_size = struct.unpack('<I', header_plus_payload[6:10])[0]
    compressed_len = struct.unpack('<I', header_plus_payload[10:14])[0]
    expected_hash = header_plus_payload[14:46]
    filename_len = struct.unpack('<H', header_plus_payload[46:48])[0]
    filename = header_plus_payload[48:48 + filename_len].decode('utf-8')
    compressed_payload = header_plus_payload[48 + filename_len: 48 + filename_len + compressed_len]
    if len(compressed_payload) != compressed_len:
        raise ValueError(
            f"compressed payload truncated: got {len(compressed_payload)}, expected {compressed_len}"
        )
    return {
        'magic': magic,
        'version': version,
        'comp_method': comp_method,
        'original_size': original_size,
        'compressed_len': compressed_len,
        'expected_hash': expected_hash,
        'filename': filename,
        'compressed_payload': compressed_payload,
    }
