#!/usr/bin/env python3
"""
Aurexis E/D — Standalone AXP6 Decoder
======================================

Decodes an Aurexis AXP6 PNG back to the exact original file.
Byte-exact, SHA-256 verified.

Usage:
    python aurexis_decode.py encoded.png
    python aurexis_decode.py encoded.png -o output_dir/
    python aurexis_decode.py encoded.png --info

Requirements:
    Python 3.6+ with standard library only (no pip installs needed).
    Uses: zlib, hashlib, struct, sys, os — all built-in.

    For Brotli-compressed files (most AXP6 PNGs use Brotli):
        pip install brotli

    If brotli is not installed and the PNG was Brotli-compressed,
    the decoder will tell you to install it.
"""

import sys
import os
import zlib
import hashlib
import struct
import math

# Try to import brotli — needed for most AXP6 files
try:
    import brotli
    HAS_BROTLI = True
except ImportError:
    HAS_BROTLI = False

# ── Constants ────────────────────────────────────────────────

BLOCK_SIZE = 8
MODULES_PER_BLOCK = BLOCK_SIZE * BLOCK_SIZE  # 64

TIER_CORE = 0
TIER_BODY = 1
TIER_EDGE = 2

PARITY_GROUP_CORE = 8
PARITY_GROUP_BODY = 16

MAGIC = b'AXP6'
HEADER_FIXED = 48


# ── PNG Reader (2-bit indexed) ───────────────────────────────

def read_indexed_png(data: bytes):
    """Read a 2-bit indexed PNG and return (width, height, module_data).
    module_data is a flat list of 2-bit values (0-3), row-major."""

    # Verify PNG signature
    sig = bytes([137, 80, 78, 71, 13, 10, 26, 10])
    if data[:8] != sig:
        raise ValueError("Not a valid PNG file")

    pos = 8
    width = height = 0
    idat_parts = []

    while pos < len(data):
        chunk_len = struct.unpack('>I', data[pos:pos+4])[0]
        pos += 4
        chunk_type = data[pos:pos+4].decode('ascii')
        pos += 4
        chunk_data = data[pos:pos+chunk_len]
        pos += chunk_len
        pos += 4  # CRC

        if chunk_type == 'IHDR':
            width = struct.unpack('>I', chunk_data[0:4])[0]
            height = struct.unpack('>I', chunk_data[4:8])[0]
            bit_depth = chunk_data[8]
            color_type = chunk_data[9]
            if bit_depth != 2 or color_type != 3:
                raise ValueError(f"Expected 2-bit indexed PNG, got depth={bit_depth} type={color_type}")
        elif chunk_type == 'IDAT':
            idat_parts.append(chunk_data)
        elif chunk_type == 'IEND':
            break

    compressed = b''.join(idat_parts)
    raw = zlib.decompress(compressed)

    bytes_per_row = math.ceil(width / 4)
    module_data = bytearray(width * height)

    for y in range(height):
        row_start = y * (1 + bytes_per_row)
        filter_type = raw[row_start]

        row_buf = bytearray(bytes_per_row)
        if filter_type == 0:  # None
            row_buf[:] = raw[row_start+1:row_start+1+bytes_per_row]
        elif filter_type == 1:  # Sub
            for i in range(bytes_per_row):
                a = row_buf[i-1] if i >= 1 else 0
                row_buf[i] = (raw[row_start+1+i] + a) & 0xFF
        elif filter_type == 2:  # Up
            for i in range(bytes_per_row):
                if y > 0:
                    prev_row_start = (y-1) * (1 + bytes_per_row)
                    # Need to reconstruct previous row too — but we already have it
                    # Actually for filter=Up, we need the already-decoded previous row
                    # This is tricky — let's do a proper two-pass or accumulate
                    pass
                row_buf[i] = raw[row_start+1+i]  # fallback
            # For safety, re-decode with proper filter handling below
        else:
            raise ValueError(f"Unsupported PNG filter type: {filter_type}")

        for x in range(width):
            byte_idx = x // 4
            bit_shift = 6 - (x % 4) * 2
            module_data[y * width + x] = (row_buf[byte_idx] >> bit_shift) & 0x03

    # If we hit filter type 2, do a full proper decode
    # Actually, let's just do a proper full decode that handles all basic filters
    has_complex_filters = False
    for y in range(height):
        row_start = y * (1 + bytes_per_row)
        if raw[row_start] not in (0, 1):
            has_complex_filters = True
            break

    if has_complex_filters:
        module_data = _decode_png_full(raw, width, height, bytes_per_row)

    return width, height, module_data


def _decode_png_full(raw: bytes, width: int, height: int, bytes_per_row: int):
    """Full PNG filter decode supporting filter types 0-4."""
    prev_row = bytearray(bytes_per_row)
    module_data = bytearray(width * height)

    for y in range(height):
        row_start = y * (1 + bytes_per_row)
        filter_type = raw[row_start]
        cur_row = bytearray(bytes_per_row)

        for i in range(bytes_per_row):
            x_val = raw[row_start + 1 + i]
            a = cur_row[i-1] if i >= 1 else 0
            b = prev_row[i]
            c = prev_row[i-1] if i >= 1 else 0

            if filter_type == 0:
                cur_row[i] = x_val
            elif filter_type == 1:  # Sub
                cur_row[i] = (x_val + a) & 0xFF
            elif filter_type == 2:  # Up
                cur_row[i] = (x_val + b) & 0xFF
            elif filter_type == 3:  # Average
                cur_row[i] = (x_val + (a + b) // 2) & 0xFF
            elif filter_type == 4:  # Paeth
                cur_row[i] = (x_val + _paeth(a, b, c)) & 0xFF
            else:
                raise ValueError(f"Unknown PNG filter type: {filter_type}")

        for x in range(width):
            byte_idx = x // 4
            bit_shift = 6 - (x % 4) * 2
            module_data[y * width + x] = (cur_row[byte_idx] >> bit_shift) & 0x03

        prev_row = cur_row

    return module_data


def _paeth(a, b, c):
    """PNG Paeth predictor."""
    p = a + b - c
    pa = abs(p - a)
    pb = abs(p - b)
    pc = abs(p - c)
    if pa <= pb and pa <= pc:
        return a
    elif pb <= pc:
        return b
    return c


# ── Module ↔ Byte conversion ────────────────────────────────

def modules_to_bytes(modules, byte_count):
    """Convert 2-bit module values back to bytes. 4 modules = 1 byte."""
    result = bytearray(byte_count)
    for i in range(byte_count):
        base = i * 4
        result[i] = (
            ((modules[base] & 0x03) << 6) |
            ((modules[base+1] & 0x03) << 4) |
            ((modules[base+2] & 0x03) << 2) |
            (modules[base+3] & 0x03)
        )
    return bytes(result)


def bytes_to_modules(data):
    """Convert bytes to 2-bit module values. 1 byte = 4 modules."""
    modules = bytearray(len(data) * 4)
    for i, b in enumerate(data):
        modules[i*4]   = (b >> 6) & 0x03
        modules[i*4+1] = (b >> 4) & 0x03
        modules[i*4+2] = (b >> 2) & 0x03
        modules[i*4+3] = b & 0x03
    return modules


# ── Tier assignment ──────────────────────────────────────────

def assign_tiers(blocks_w, data_blocks_h):
    """Assign each data block to CORE/BODY/EDGE tier based on distance from edge."""
    core_blocks = []
    body_blocks = []
    edge_blocks = []
    tier_map = [0] * (blocks_w * data_blocks_h)

    for by in range(data_blocks_h):
        for bx in range(blocks_w):
            dist = min(bx, by, blocks_w - 1 - bx, data_blocks_h - 1 - by)

            if blocks_w < 5 or data_blocks_h < 5:
                tier = TIER_CORE
            elif blocks_w < 9 or data_blocks_h < 9:
                tier = TIER_EDGE if dist == 0 else TIER_CORE
            else:
                if dist == 0:
                    tier = TIER_EDGE
                elif dist == 1:
                    tier = TIER_BODY
                else:
                    tier = TIER_CORE

            idx = by * blocks_w + bx
            tier_map[idx] = tier

            if tier == TIER_CORE:
                core_blocks.append(idx)
            elif tier == TIER_BODY:
                body_blocks.append(idx)
            else:
                edge_blocks.append(idx)

    return tier_map, core_blocks, body_blocks, edge_blocks


# ── De-interleave ────────────────────────────────────────────

def tier_deinterleave(interleaved, num_blocks, per_block, total_modules):
    """Reverse tier-aware interleaving to get original module order."""
    modules = bytearray(total_modules)
    for i in range(total_modules):
        block = i % num_blocks
        pos = i // num_blocks
        modules[i] = interleaved[block * per_block + pos]
    return modules


# ── Manifest reader ──────────────────────────────────────────

def read_manifest(module_data, width, blocks_w):
    """Read manifest from header row (row 0, between sync columns)."""
    manifest_start_x = BLOCK_SIZE
    manifest_width = (blocks_w - 2) * BLOCK_SIZE
    manifest = bytearray(manifest_width * BLOCK_SIZE)

    for y in range(BLOCK_SIZE):
        for x in range(manifest_width):
            manifest[y * manifest_width + x] = module_data[y * width + manifest_start_x + x]

    # Check magic: 0,1,2,3
    if manifest[0] != 0 or manifest[1] != 1 or manifest[2] != 2 or manifest[3] != 3:
        raise ValueError("Not an AXP6 carrier (manifest magic mismatch)")

    def read_u8(off):
        return modules_to_bytes(manifest[off:off+4], 1)[0]

    def read_u16(off):
        return struct.unpack('<H', modules_to_bytes(manifest[off:off+8], 2))[0]

    def read_u32(off):
        return struct.unpack('<I', modules_to_bytes(manifest[off:off+16], 4))[0]

    version = read_u8(4)
    if version not in (6, 7):
        raise ValueError(f"Unsupported AXP version: {version} (expected 6 or 7)")

    if version == 6:
        # v6: block/parity counts are U16
        return {
            'payload_bytes': read_u32(12),
            'grid_width': read_u32(28),
            'block_size': read_u8(44),
            'blocks_w': read_u16(48),
            'data_blocks_h': read_u16(56),
            'core_block_count': read_u16(64),
            'body_block_count': read_u16(72),
            'edge_block_count': read_u16(80),
            'core_parity_count': read_u16(88),
            'body_parity_count': read_u16(96),
            'core_group_size': read_u8(104),
            'body_group_size': read_u8(108),
        }
    else:
        # v7: block/parity counts widened to U32
        return {
            'payload_bytes': read_u32(12),
            'grid_width': read_u32(28),
            'block_size': read_u8(44),
            'blocks_w': read_u32(48),
            'data_blocks_h': read_u32(64),
            'core_block_count': read_u32(80),
            'body_block_count': read_u32(96),
            'edge_block_count': read_u32(112),
            'core_parity_count': read_u32(128),
            'body_parity_count': read_u32(144),
            'core_group_size': read_u8(160),
            'body_group_size': read_u8(164),
        }


# ── Block extraction ─────────────────────────────────────────

def extract_tier_blocks(module_data, width, block_indices, per_block, blocks_w, data_row_start=1):
    """Extract interleaved module data for a set of blocks belonging to one tier."""
    interleaved = bytearray(len(block_indices) * per_block)

    for t, block_idx in enumerate(block_indices):
        by = block_idx // blocks_w
        bx = block_idx % blocks_w
        py_base = (data_row_start + by) * BLOCK_SIZE
        block_data_start = t * per_block

        for ly in range(BLOCK_SIZE):
            for lx in range(BLOCK_SIZE):
                module_idx = ly * BLOCK_SIZE + lx
                px = bx * BLOCK_SIZE + lx
                py = py_base + ly
                if module_idx < per_block:
                    interleaved[block_data_start + module_idx] = module_data[py * width + px]

    return interleaved


# ── CRC-8 (for integrity verification) ──────────────────────

def _build_crc8_table():
    table = [0] * 256
    for i in range(256):
        c = i
        for _ in range(8):
            c = ((c << 1) ^ 0x07) if (c & 0x80) else (c << 1)
        table[i] = c & 0xFF
    return table

CRC8_TABLE = _build_crc8_table()

def crc8_linked(data, start, length, neighbor_crcs):
    """Compute neighborhood-linked CRC-8."""
    crc = 0
    for i in range(start, start + length):
        crc = CRC8_TABLE[crc ^ data[i]]
    for nc in neighbor_crcs:
        crc = CRC8_TABLE[crc ^ nc]
    return crc


def compute_linked_crcs(block_lookup, blocks_w, data_blocks_h):
    """Compute all neighborhood-linked CRC-8 values in raster order."""
    total = blocks_w * data_blocks_h
    crc_values = bytearray(total)

    for by in range(data_blocks_h):
        for bx in range(blocks_w):
            b = by * blocks_w + bx
            info = block_lookup[b]
            block_start = info['local_idx'] * info['per_block']
            block_len = min(info['per_block'], len(info['data']) - block_start)

            neighbors = []
            if bx > 0:
                neighbors.append(crc_values[by * blocks_w + (bx - 1)])
            if by > 0:
                neighbors.append(crc_values[(by - 1) * blocks_w + bx])

            crc_values[b] = crc8_linked(info['data'], block_start, block_len, neighbors)

    return crc_values


# ── Main decode ──────────────────────────────────────────────

def decode(png_path, output_dir=None, info_only=False):
    """Decode an AXP6 PNG back to the original file.

    Returns dict with decode metadata including filename, sizes, SHA-256, etc.
    """
    with open(png_path, 'rb') as f:
        png_data = f.read()

    png_size = len(png_data)
    width, height, module_data = read_indexed_png(png_data)
    blocks_w = width // BLOCK_SIZE

    # Read manifest
    manifest = read_manifest(module_data, width, blocks_w)
    data_blocks_h = manifest['data_blocks_h']
    total_data_blocks = blocks_w * data_blocks_h
    payload_bytes = manifest['payload_bytes']
    data_modules = payload_bytes * 4

    # Reconstruct tier assignment
    tier_map, core_blocks, body_blocks, edge_blocks = assign_tiers(blocks_w, data_blocks_h)

    # Verify tier counts match manifest
    if len(core_blocks) != manifest['core_block_count']:
        raise ValueError(f"Core block count mismatch: {len(core_blocks)} vs {manifest['core_block_count']}")
    if len(body_blocks) != manifest['body_block_count']:
        raise ValueError(f"Body block count mismatch: {len(body_blocks)} vs {manifest['body_block_count']}")
    if len(edge_blocks) != manifest['edge_block_count']:
        raise ValueError(f"Edge block count mismatch: {len(edge_blocks)} vs {manifest['edge_block_count']}")

    # Compute tier capacities and partition sizes
    core_cap = len(core_blocks) * MODULES_PER_BLOCK
    body_cap = len(body_blocks) * MODULES_PER_BLOCK
    total_modules = data_modules

    core_modules = min(total_modules, core_cap)
    body_modules = min(total_modules - core_modules, body_cap)
    edge_modules = total_modules - core_modules - body_modules

    core_per_block = math.ceil(core_modules / len(core_blocks)) if core_blocks else 0
    body_per_block = math.ceil(body_modules / len(body_blocks)) if body_blocks else 0
    edge_per_block = math.ceil(edge_modules / len(edge_blocks)) if edge_blocks else 0

    # Extract interleaved data per tier
    core_int = extract_tier_blocks(module_data, width, core_blocks, core_per_block, blocks_w)
    body_int = extract_tier_blocks(module_data, width, body_blocks, body_per_block, blocks_w)
    edge_int = extract_tier_blocks(module_data, width, edge_blocks, edge_per_block, blocks_w)

    # ── Verify parity ──
    core_parity_count = manifest['core_parity_count']
    body_parity_count = manifest['body_parity_count']

    parity_row_start = 1 + data_blocks_h
    core_parity_modules = core_parity_count * core_per_block
    body_parity_modules = body_parity_count * body_per_block
    total_parity_modules = core_parity_modules + body_parity_modules

    parity_pixel_rows_needed = math.ceil(total_parity_modules / (blocks_w * BLOCK_SIZE)) if total_parity_modules > 0 else 0
    parity_block_rows = max(1, math.ceil(parity_pixel_rows_needed / BLOCK_SIZE)) if parity_pixel_rows_needed > 0 else 0
    parity_pixel_rows = parity_block_rows * BLOCK_SIZE
    parity_start_y = parity_row_start * BLOCK_SIZE

    parity_verified = True
    if total_parity_modules > 0:
        all_parity = bytearray(total_parity_modules)
        p_idx = 0
        for y in range(parity_pixel_rows):
            for x in range(width):
                if p_idx >= total_parity_modules:
                    break
                py = parity_start_y + y
                all_parity[p_idx] = module_data[py * width + x]
                p_idx += 1

        # Verify core parity
        if core_parity_count > 0 and core_per_block > 0:
            stored_core_parity = all_parity[:core_parity_modules]
            recomputed = _compute_tier_parity(core_int, len(core_blocks), core_per_block, manifest['core_group_size'])
            if recomputed != stored_core_parity:
                parity_verified = False

        # Verify body parity
        if body_parity_count > 0 and body_per_block > 0:
            stored_body_parity = all_parity[core_parity_modules:core_parity_modules + body_parity_modules]
            recomputed = _compute_tier_parity(body_int, len(body_blocks), body_per_block, manifest['body_group_size'])
            if recomputed != stored_body_parity:
                parity_verified = False

    if not parity_verified:
        raise ValueError("Parity verification failed — data may be corrupted")

    # ── Verify integrity (neighborhood-linked CRC-8) ──
    integrity_row_start = 1 + data_blocks_h + parity_block_rows
    int_crc_modules_needed = total_data_blocks * 4
    int_pixel_rows_needed = math.ceil(int_crc_modules_needed / (blocks_w * BLOCK_SIZE))
    int_block_rows = max(1, math.ceil(int_pixel_rows_needed / BLOCK_SIZE))
    int_pixel_rows = int_block_rows * BLOCK_SIZE
    int_start_y = integrity_row_start * BLOCK_SIZE

    # Read stored CRCs
    int_module_data = bytearray(width * int_pixel_rows)
    for y in range(int_pixel_rows):
        for x in range(width):
            int_module_data[y * width + x] = module_data[(int_start_y + y) * width + x]
    expected_crcs = modules_to_bytes(int_module_data[:total_data_blocks * 4], total_data_blocks)

    # Build block lookup
    block_lookup = [None] * total_data_blocks
    for t, idx in enumerate(core_blocks):
        block_lookup[idx] = {'data': core_int, 'local_idx': t, 'per_block': core_per_block}
    for t, idx in enumerate(body_blocks):
        block_lookup[idx] = {'data': body_int, 'local_idx': t, 'per_block': body_per_block}
    for t, idx in enumerate(edge_blocks):
        block_lookup[idx] = {'data': edge_int, 'local_idx': t, 'per_block': edge_per_block}

    recomputed_crcs = compute_linked_crcs(block_lookup, blocks_w, data_blocks_h)

    integrity_errors = sum(1 for b in range(total_data_blocks) if recomputed_crcs[b] != expected_crcs[b])
    if integrity_errors > 0:
        raise ValueError(f"Integrity check failed: {integrity_errors}/{total_data_blocks} blocks corrupted")

    # ── De-interleave each tier ──
    core_seg = tier_deinterleave(core_int, len(core_blocks), core_per_block, core_modules) if core_blocks else bytearray()
    body_seg = tier_deinterleave(body_int, len(body_blocks), body_per_block, body_modules) if body_blocks else bytearray()
    edge_seg = tier_deinterleave(edge_int, len(edge_blocks), edge_per_block, edge_modules) if edge_blocks else bytearray()

    # Reassemble payload
    raw_modules = bytearray(core_seg) + bytearray(body_seg) + bytearray(edge_seg)
    payload = modules_to_bytes(raw_modules, payload_bytes)

    # ── Parse AXP6 header ──
    magic = payload[:4]
    if magic != MAGIC:
        raise ValueError(f"Not AXP6 (magic: {magic.hex()})")

    off = 4
    version = payload[off]; off += 1
    comp_method = payload[off]; off += 1
    original_size = struct.unpack('<I', payload[off:off+4])[0]; off += 4
    compressed_len = struct.unpack('<I', payload[off:off+4])[0]; off += 4
    expected_hash = payload[off:off+32]; off += 32
    filename_len = struct.unpack('<H', payload[off:off+2])[0]; off += 2
    filename = payload[off:off+filename_len].decode('utf-8'); off += filename_len

    compressed = payload[off:off+compressed_len]

    if info_only:
        return {
            'filename': filename,
            'original_size': original_size,
            'compressed_size': compressed_len,
            'compression': 'brotli' if comp_method == 1 else 'deflate',
            'png_size': png_size,
            'ratio_percent': f"{png_size / original_size * 100:.1f}",
            'dimensions': f"{width}x{height}",
            'blocks': f"{blocks_w}x{data_blocks_h}",
            'tiers': f"CORE={len(core_blocks)} BODY={len(body_blocks)} EDGE={len(edge_blocks)}",
            'expected_sha256': expected_hash.hex(),
            'parity_verified': parity_verified,
            'integrity_verified': integrity_errors == 0,
        }

    # ── Decompress ──
    if comp_method == 1:  # Brotli
        if not HAS_BROTLI:
            print("\nERROR: This file was compressed with Brotli.")
            print("Install it with:  pip install brotli")
            print("Then re-run this decoder.")
            sys.exit(1)
        decompressed = brotli.decompress(bytes(compressed))
    elif comp_method == 0:  # Deflate
        decompressed = zlib.decompress(bytes(compressed))
    else:
        raise ValueError(f"Unknown compression method: {comp_method}")

    if len(decompressed) != original_size:
        raise ValueError(f"Size mismatch: expected {original_size}, got {len(decompressed)}")

    # ── SHA-256 verify ──
    actual_hash = hashlib.sha256(decompressed).digest()
    if actual_hash != expected_hash:
        raise ValueError(f"SHA-256 MISMATCH!\n  Expected: {expected_hash.hex()}\n  Got:      {actual_hash.hex()}")

    # ── Write output ──
    if output_dir is None:
        output_dir = os.path.dirname(os.path.abspath(png_path))
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, filename)
    with open(output_path, 'wb') as f:
        f.write(decompressed)

    return {
        'filename': filename,
        'output_path': output_path,
        'original_size': original_size,
        'compressed_size': compressed_len,
        'png_size': png_size,
        'compression': 'brotli' if comp_method == 1 else 'deflate',
        'ratio_percent': f"{png_size / original_size * 100:.1f}",
        'sha256': actual_hash.hex(),
        'sha256_verified': True,
        'parity_verified': parity_verified,
        'integrity_verified': integrity_errors == 0,
        'dimensions': f"{width}x{height}",
        'blocks': f"{blocks_w}x{data_blocks_h}",
        'tiers': {
            'core': len(core_blocks),
            'body': len(body_blocks),
            'edge': len(edge_blocks),
        },
    }


def _compute_tier_parity(interleaved_data, num_blocks, per_block, group_size):
    """Compute XOR parity for a tier's interleaved data."""
    if group_size == 0 or num_blocks == 0:
        return bytearray()

    parity_count = math.ceil(num_blocks / group_size)
    parity_data = bytearray(parity_count * per_block)

    for g in range(parity_count):
        parity_start = g * per_block
        group_start = g * group_size
        group_end = min(group_start + group_size, num_blocks)

        for b in range(group_start, group_end):
            block_start = b * per_block
            for m in range(per_block):
                parity_data[parity_start + m] ^= interleaved_data[block_start + m]

    return parity_data


# ── CLI ──────────────────────────────────────────────────────

def main():
    if len(sys.argv) < 2 or sys.argv[1] in ('-h', '--help'):
        print(__doc__)
        print("Usage:")
        print("  python aurexis_decode.py <file.png>              Decode to same directory")
        print("  python aurexis_decode.py <file.png> -o <dir>     Decode to specified directory")
        print("  python aurexis_decode.py <file.png> --info       Show file info without decoding")
        print()
        print("Brotli support:")
        if HAS_BROTLI:
            print("  brotli module: INSTALLED (ready)")
        else:
            print("  brotli module: NOT INSTALLED")
            print("  Install with:  pip install brotli")
        sys.exit(0)

    png_path = sys.argv[1]
    if not os.path.isfile(png_path):
        print(f"ERROR: File not found: {png_path}")
        sys.exit(1)

    output_dir = None
    info_only = False
    i = 2
    while i < len(sys.argv):
        if sys.argv[i] == '-o' and i + 1 < len(sys.argv):
            output_dir = sys.argv[i + 1]
            i += 2
        elif sys.argv[i] == '--info':
            info_only = True
            i += 1
        else:
            print(f"Unknown argument: {sys.argv[i]}")
            sys.exit(1)

    print()
    print("╔══════════════════════════════════════════════════════════╗")
    print("║         Aurexis E/D — AXP6 Decoder (Python)            ║")
    print("╚══════════════════════════════════════════════════════════╝")
    print()

    try:
        result = decode(png_path, output_dir, info_only)
    except Exception as e:
        print(f"  DECODE FAILED: {e}")
        sys.exit(1)

    if info_only:
        print(f"  File info for: {os.path.basename(png_path)}")
        print(f"  ─────────────────────────────────────────")
        print(f"  Original filename:  {result['filename']}")
        print(f"  Original size:      {result['original_size']:,} bytes")
        print(f"  Compressed size:    {result['compressed_size']:,} bytes")
        print(f"  PNG size:           {result['png_size']:,} bytes")
        print(f"  Ratio:              {result['ratio_percent']}%")
        print(f"  Compression:        {result['compression']}")
        print(f"  Dimensions:         {result['dimensions']}")
        print(f"  Grid:               {result['blocks']} data blocks")
        print(f"  Tiers:              {result['tiers']}")
        print(f"  Expected SHA-256:   {result['expected_sha256'][:32]}...")
        print(f"  Parity verified:    {'YES' if result['parity_verified'] else 'FAIL'}")
        print(f"  Integrity verified: {'YES' if result['integrity_verified'] else 'FAIL'}")
    else:
        orig_kb = result['original_size'] / 1024
        png_kb = result['png_size'] / 1024
        if orig_kb >= 1024:
            orig_str = f"{orig_kb/1024:.1f} MB"
        else:
            orig_str = f"{orig_kb:.1f} KB"
        if png_kb >= 1024:
            png_str = f"{png_kb/1024:.1f} MB"
        else:
            png_str = f"{png_kb:.1f} KB"

        print(f"  Input:       {os.path.basename(png_path)} ({png_str})")
        print(f"  Output:      {result['filename']} ({orig_str})")
        print(f"  Compression: {result['compression']}")
        print(f"  Ratio:       {result['ratio_percent']}% (PNG was {result['ratio_percent']}% of original)")
        print()
        print(f"  SHA-256:     {result['sha256']}")
        print(f"  Verified:    YES — byte-exact match")
        print(f"  Parity:      {'VERIFIED' if result['parity_verified'] else 'FAILED'}")
        print(f"  Integrity:   {'VERIFIED' if result['integrity_verified'] else 'FAILED'}")
        print()
        print(f"  Saved to:    {result['output_path']}")

    print()
    print("══════════════════════════════════════════════════════════")
    if info_only:
        print("  INFO COMPLETE")
    else:
        print("  DECODE COMPLETE — file restored, SHA-256 verified")
    print("══════════════════════════════════════════════════════════")
    print()


if __name__ == '__main__':
    main()
