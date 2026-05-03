# 01 — AXP6 Architecture Digest (verified against `aurexis_decode.py`)

> A from-source description of what AXP6 actually is, with file-and-line citations. The phrase "AXP6's deep architectural commitment is the pixel-grid carrier" is defended at the end of this document. If anything in this digest is wrong, the proposal that builds on it is wrong — so the reviewer should scrutinize this doc before any other.

**Source of truth for this digest:** `aurexis_decode.py` (737 lines, present in this repo at `/home/user/Crypscan/aurexis_decode.py`). All line citations refer to that file unless otherwise noted.

**Confirmed working:** the standalone decoder roundtrips an Aurexis-encoded PNG to a byte-exact original file with SHA-256 verification (`DECODE_GUIDE.md` lines 81–85). The 30 MB sample-2.mp4 video encoded into an 11032×13120 PNG (handoff §"Local files") is the canonical demonstration; this digest is consistent with that artifact even though Phase 0 did not load the PNG itself.

---

## 1. Container at a glance

| Layer | Substrate |
|---|---|
| **Outermost** | A 2-bit indexed PNG (color type 3, bit depth 2). One image pixel encodes one "module" with value ∈ {0, 1, 2, 3}. |
| **Synchronization** | Sync columns in the leftmost and rightmost block columns (used for grid alignment; not parsed by the decoder explicitly but reserved by the manifest layout). |
| **Header row** | The first BLOCK_SIZE×BLOCK_SIZE module row, between the sync columns, holds the manifest. |
| **Data rows** | `data_blocks_h` rows of `blocks_w` 8×8 module blocks, each block belonging to one of three positional tiers. |
| **Parity rows** | Per-tier XOR parity blocks computed inside each tier's interleaved stream. |
| **Integrity rows** | One byte (4 modules) of neighborhood-linked CRC-8 per data block, in raster order. |
| **Innermost** | Compressed payload (Brotli or Deflate) wrapping a fixed-size header (`AXP6` magic + version + comp method + sizes + 32-byte SHA-256 + filename) followed by the original file bytes. |

Decode is the strict inverse of encode: read PNG → unpack modules → read manifest → reconstruct tiers → de-interleave → verify parity → verify linked CRC → assemble payload → strip inner header → decompress → SHA-256 verify → write file.

## 2. Constants and module representation

From `aurexis_decode.py` lines 39–52:

```python
BLOCK_SIZE = 8
MODULES_PER_BLOCK = BLOCK_SIZE * BLOCK_SIZE  # 64

TIER_CORE = 0
TIER_BODY = 1
TIER_EDGE = 2

PARITY_GROUP_CORE = 8
PARITY_GROUP_BODY = 16

MAGIC = b'AXP6'
HEADER_FIXED = 48
```

**Module ↔ byte conversion** (lines 195–217): four 2-bit modules pack into one byte, MSB-first per module within the byte:

```python
result[i] = (
    ((modules[base]   & 0x03) << 6) |
    ((modules[base+1] & 0x03) << 4) |
    ((modules[base+2] & 0x03) << 2) |
    ((modules[base+3] & 0x03))
)
```

Bytes-to-modules is the symmetric inverse. The module is the atomic unit of the carrier; everything above sits on top of "the module is a 2-bit cell at a known pixel coordinate."

## 3. PNG reader

`read_indexed_png()` (lines 57–138) parses the PNG manually using only `zlib` and `struct`. It accepts only color type 3 (indexed) at bit depth 2 (line 84). Filter-type-0 and filter-type-1 rows are decoded inline; if any other filter type is present (Up=2, Average=3, Paeth=4), the function falls back to `_decode_png_full()` (lines 141–177), which carries `prev_row` and applies the standard PNG predictor including Paeth (`_paeth()` at lines 180–190). This is canonical PNG, not a custom transport.

The output of the PNG reader is a flat module array of length `width × height` with values 0–3 (line 95).

## 4. Manifest

The manifest sits in the header row, between the sync columns (`read_manifest()`, lines 272–330). The manifest area has `manifest_width = (blocks_w - 2) * BLOCK_SIZE` modules wide and `BLOCK_SIZE` modules tall (lines 274–276).

### 4.1 Magic check

The first four modules must be the literal sequence `0, 1, 2, 3` (lines 282–284):

```python
if manifest[0] != 0 or manifest[1] != 1 or manifest[2] != 2 or manifest[3] != 3:
    raise ValueError("Not an AXP6 carrier (manifest magic mismatch)")
```

This is the file-format identifier — distinct from the inner `AXP6` ASCII magic at byte offset 0 of the *payload* (see §9).

### 4.2 Version dispatch

`version = read_u8(4)`; only versions 6 and 7 are accepted (lines 295–297). v6 stores block/parity counts as `u16`; v7 widens them to `u32` to support carriers larger than 65,535 blocks per tier (lines 299–330). The 11032×13120 sample carrier referenced in the handoff has `blocks_w = 11032/8 = 1379` and `data_blocks_h ≈ 1640 - (header + parity + integrity rows)`, giving on the order of 2.2 million data blocks — well into v7 territory.

### 4.3 Manifest fields (v7 layout shown; v6 narrows the same fields)

| Field | Offset (modules) | Width | Meaning |
|---|---:|---|---|
| magic 0,1,2,3 | 0 | 4 modules | format identifier |
| version | 4 | 1 byte (4 modules) | 6 or 7 |
| (reserved) | 5–11 | — | (gap consistent with reserved bytes) |
| `payload_bytes` | 12 | u32 (16 modules) | total bytes of payload-after-modulation |
| (reserved) | 16–27 | — | |
| `grid_width` | 28 | u32 (16 modules) | width in pixels |
| (reserved) | 32–43 | — | |
| `block_size` | 44 | u8 (4 modules) | 8 |
| `blocks_w` | 48 | u32 v7 / u16 v6 | data-block columns |
| `data_blocks_h` | 64 | u32 v7 / u16 v6 | data-block rows |
| `core_block_count` | 80 | u32 v7 / u16 v6 | size of CORE tier in blocks |
| `body_block_count` | 96 | u32 v7 / u16 v6 | size of BODY tier in blocks |
| `edge_block_count` | 112 | u32 v7 / u16 v6 | size of EDGE tier in blocks |
| `core_parity_count` | 128 | u32 v7 / u16 v6 | parity blocks per CORE tier |
| `body_parity_count` | 144 | u32 v7 / u16 v6 | parity blocks per BODY tier |
| `core_group_size` | 160 | u8 (4 modules) | parity group size for CORE (default 8) |
| `body_group_size` | 164 | u8 (4 modules) | parity group size for BODY (default 16) |

Offsets above are in *module units*, which is what the decoder reads directly. Each `u32` consumes 16 modules (4 bytes × 4 modules/byte); each `u16` consumes 8 modules; each `u8` consumes 4 modules.

The manifest is recovered before any other decode step, because every subsequent step needs `blocks_w`, `data_blocks_h`, the per-tier counts, and the parity group sizes.

## 5. Tier assignment

`assign_tiers(blocks_w, data_blocks_h)` at lines 222–255 is the geometric core of AXP6. For each block at position (bx, by), define `dist = min(bx, by, blocks_w - 1 - bx, data_blocks_h - 1 - by)`. Then:

```python
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
```

In words:
- **EDGE** = blocks on the outer ring (`dist == 0`).
- **BODY** = blocks one ring in from the edge (`dist == 1`).
- **CORE** = everything inside.

For tiny carriers the rules collapse into all-CORE; for medium ones into EDGE-and-CORE; for full-size carriers (the sample carrier and any practical use) into EDGE/BODY/CORE in concentric rings.

This is the deep architectural commitment defended at the end of this document: tier identity is a function of *block coordinates in the pixel grid*. There is no other definition; there is no other input to `assign_tiers()` than `blocks_w` and `data_blocks_h`. If the pixel grid is unknown to the decoder, no tier can be assigned. If no tier can be assigned, no parity can be verified, no CRC can be checked, no de-interleave can be performed, no payload can be assembled.

After tier classification, the decoder recomputes the per-tier block counts and **verifies them against the manifest** (lines 427–432). A tier-count mismatch immediately fails the decode — the manifest and `assign_tiers()` are required to be consistent.

## 6. Per-tier interleaved extraction

`extract_tier_blocks(module_data, width, block_indices, per_block, blocks_w, data_row_start=1)` at lines 335–353 walks each block in the given tier (in raster order on the original pixel grid), reads its 8×8 module patch, and concatenates them into a flat `interleaved` array of size `len(block_indices) * per_block`. `per_block` is the number of modules per block actually used by this tier — usually 64 (full block), but the last tier in the partition may use fewer, since payload modules are partitioned across tiers and the last block in the last tier may not be full.

The partition (lines 437–445):

```python
core_modules = min(total_modules, core_cap)
body_modules = min(total_modules - core_modules, body_cap)
edge_modules = total_modules - core_modules - body_modules

core_per_block = ceil(core_modules / len(core_blocks))
body_per_block = ceil(body_modules / len(body_blocks))
edge_per_block = ceil(edge_modules / len(edge_blocks))
```

So the payload is filled in tier order CORE → BODY → EDGE (most-protected first), with the per-block usage in each tier proportional to that tier's share of the total payload module count. CORE blocks always carry as many modules as possible before the overflow reaches BODY.

## 7. De-interleaving

After per-tier extraction, the flat `interleaved` array is the encoder's tier-aware interleave of the underlying tier payload. Decoding reverses it (`tier_deinterleave()`, lines 260–267):

```python
def tier_deinterleave(interleaved, num_blocks, per_block, total_modules):
    modules = bytearray(total_modules)
    for i in range(total_modules):
        block = i % num_blocks
        pos   = i // num_blocks
        modules[i] = interleaved[block * per_block + pos]
    return modules
```

In other words, module `i` of the original tier stream lives at slot `pos` of block `block` in the interleaved arrangement, where `block = i mod num_blocks`. This is a classic round-robin interleaver. Its purpose is exactly the AXP6 design intent: spread localized damage across many parity groups so a single damaged region does not concentrate inside one group and overwhelm parity recovery.

## 8. Verification — parity then CRC

### 8.1 Parity (lines 452–493, 617–635)

Per tier, parity blocks are computed by XORing all data blocks in groups of `group_size` (8 for CORE, 16 for BODY by default). The decoder recomputes parity from the recovered tier data and compares against the stored parity blocks (read from the parity row span at `parity_row_start = 1 + data_blocks_h`):

```python
recomputed = _compute_tier_parity(core_int, len(core_blocks), core_per_block, manifest['core_group_size'])
if recomputed != stored_core_parity:
    parity_verified = False
```

If parity does not match, `decode()` raises `"Parity verification failed — data may be corrupted"`. The Python decoder reports the failure but does *not* perform parity-based recovery — the Python decoder is read-only verification (`DECODE_GUIDE.md` lines 110–112: "If only a few blocks, the parity system might have recovered them (in the Node decoder). This Python decoder doesn't do recovery — it reports the error.").

EDGE tier carries no parity. The reasoning is structural: EDGE blocks are the most exposed to physical damage and the least trusted; instead of protecting EDGE with its own parity, AXP6 places the most-damageable carrier modules in the tier that is verified only by CRC, and concentrates parity protection on CORE and BODY where damage is statistically rarer.

### 8.2 Neighborhood-linked CRC-8 (lines 369–399)

The CRC scheme is the most distinctive part of AXP6's defense. The polynomial is the standard CRC-8 ATM generator (`0x07`, `_build_crc8_table()` at lines 358–367). The "linked" part is in `crc8_linked()` (lines 369–376):

```python
def crc8_linked(data, start, length, neighbor_crcs):
    crc = 0
    for i in range(start, start + length):
        crc = CRC8_TABLE[crc ^ data[i]]
    for nc in neighbor_crcs:
        crc = CRC8_TABLE[crc ^ nc]
    return crc
```

Per block, after computing CRC over its own bytes, the result is XORed against the CRC values of its left neighbor and its above neighbor (`compute_linked_crcs()`, lines 379–399):

```python
neighbors = []
if bx > 0:
    neighbors.append(crc_values[by * blocks_w + (bx - 1)])
if by > 0:
    neighbors.append(crc_values[(by - 1) * blocks_w + bx])

crc_values[b] = crc8_linked(info['data'], block_start, block_len, neighbors)
```

This is the "neighborhood-linked CRC-8" referenced in `DECODE_GUIDE.md` line 93. The effect: a single corrupted block's CRC mismatch propagates one block right and one block down, making the failure pattern identifiable even for damage that strictly respects block boundaries. It is detection + localization, not correction.

If any of the recomputed CRCs disagree with the stored CRCs (read from the integrity row span at `integrity_row_start = 1 + data_blocks_h + parity_block_rows`, lines 496–509), the decoder raises with the count of corrupted blocks (lines 521–523).

## 9. Payload reassembly

After per-tier de-interleave, the three tier streams are concatenated in CORE | BODY | EDGE order and converted from modules to bytes (lines 526–532):

```python
raw_modules = bytearray(core_seg) + bytearray(body_seg) + bytearray(edge_seg)
payload = modules_to_bytes(raw_modules, payload_bytes)
```

The recovered byte stream begins with a fixed-format payload header (lines 535–548):

```
offset 0  : 4 bytes  magic       = b'AXP6'
offset 4  : 1 byte   version
offset 5  : 1 byte   comp_method  (0 = deflate, 1 = brotli)
offset 6  : 4 bytes  original_size (uint32 LE)
offset 10 : 4 bytes  compressed_len (uint32 LE)
offset 14 : 32 bytes expected_hash (SHA-256 of the original)
offset 46 : 2 bytes  filename_len (uint16 LE)
offset 48 : N bytes  filename (UTF-8)
offset 48+N : compressed_len bytes  compressed payload
```

The total fixed-prefix size is 48 bytes plus the variable filename — consistent with `HEADER_FIXED = 48` at line 52.

## 10. Decompression and SHA-256 verification

Brotli decode (lines 567–573):

```python
if comp_method == 1:  # Brotli
    if not HAS_BROTLI:
        print("\nERROR: This file was compressed with Brotli.")
        ...
    decompressed = brotli.decompress(bytes(compressed))
elif comp_method == 0:  # Deflate
    decompressed = zlib.decompress(bytes(compressed))
```

Then size and hash gates (lines 579–585):

```python
if len(decompressed) != original_size:
    raise ValueError(f"Size mismatch: expected {original_size}, got {len(decompressed)}")

actual_hash = hashlib.sha256(decompressed).digest()
if actual_hash != expected_hash:
    raise ValueError(f"SHA-256 MISMATCH! ...")
```

Bit-exact restoration is the gate. Anything less is a failure.

## 11. The full layout summary

For a v7 carrier of `blocks_w` × `data_blocks_h` data blocks plus parity and integrity overhead:

```
y = 0 .. BLOCK_SIZE-1                                 manifest header row
y = BLOCK_SIZE .. (1 + data_blocks_h) * BLOCK_SIZE -1 data block rows
                                                       (CORE/BODY/EDGE assigned by position)
y = (1 + data_blocks_h) * BLOCK_SIZE                   parity rows, length:
        .. + parity_block_rows * BLOCK_SIZE -1            ceil((core_parity_count*core_per_block
                                                              + body_parity_count*body_per_block)
                                                              / (blocks_w * BLOCK_SIZE))
                                                       rounded up to whole blocks
y = (1 + data_blocks_h + parity_block_rows) * BLOCK_SIZE  integrity rows: one byte (4 modules)
        .. + int_block_rows * BLOCK_SIZE -1                 of linked CRC per data block
```

Sync columns occupy block column 0 and block column `blocks_w - 1` of every row. Each pixel is one 2-bit module.

## 12. The defensible claim: AXP6's deep architectural commitment is the pixel grid

This is the single sentence the proposal (`03_PHOXOIDAL_CARRIER_ARCHITECTURE.md`) builds on. It is defended by enumerating the load-bearing functions in `aurexis_decode.py` and observing that each one assumes a known, recoverable, integer-coordinate pixel grid:

| Decoder function | Lines | Pixel-grid assumption |
|---|---|---|
| `read_indexed_png()` | 57–138 | Reads (width, height) integer dimensions from IHDR; addresses every pixel by `(y, x)` integer coordinates. |
| `assign_tiers()` | 222–255 | Computes `dist = min(bx, by, blocks_w-1-bx, data_blocks_h-1-by)` — a function purely of integer block coordinates. |
| `read_manifest()` | 272–330 | Indexes into the manifest by integer module offset within row 0. |
| `extract_tier_blocks()` | 335–353 | Iterates `(by * BLOCK_SIZE + ly, bx * BLOCK_SIZE + lx)` for every block — direct pixel addressing. |
| `tier_deinterleave()` | 260–267 | Inverts a round-robin permutation defined over an integer-indexed module sequence. |
| `_compute_tier_parity()` | 617–635 | XORs same-offset bytes across blocks identified by integer index in the tier list. |
| `compute_linked_crcs()` | 379–399 | Walks `(by, bx)` in raster order; references neighbors by `(by, bx-1)` and `(by-1, bx)`. |

Every one of these functions stops working — not "degrades," **stops** — if the decoder cannot recover the integer pixel grid. The sync columns are there *because* the grid is the load-bearing assumption; their job is to let the decoder snap to grid in a clean digital file. Real-camera capture of a printed or screen-displayed carrier breaks the grid (perspective tilt, rolling shutter shear, focus blur, lens warp, moiré), which is exactly the V2 frontier.

This is not a criticism of AXP6's design. AXP6 is well-tuned for the failure model it was designed to defend against (discrete localized corruption inside a clean digital file — see `02_FAILURE_MODEL_ANALYSIS.md` §1). The pixel grid is the right substrate for that regime. It is the wrong substrate for the *capture-mediated* regime, and that is the architectural fact the proposal builds on.

## 13. What survives across the architectural transition

The proposal in `03_PHOXOIDAL_CARRIER_ARCHITECTURE.md` preserves three things from AXP6 verbatim:

1. **Brotli compression** of the payload before symbol-encoding (matches `comp_method == 1` path, lines 567–573).
2. **SHA-256 hash** of the original payload, stored in the manifest, verified after decode (matches `expected_hash` at offset 14 of the inner header and the gate at lines 583–585).
3. **`AXP6` magic + manifest** declaring payload size, compression method, hash, encoding parameters — same role as the AXP6 manifest, different storage medium (encoded as a known-position germ cluster rather than as 2-bit modules in the header row).

The two things that do *not* survive are exactly the two that depend on the pixel grid:

1. The **2-bit module** as the atomic unit of the carrier. Replaced by the **catastrophe germ** as the atomic unit.
2. The **positional tier system** (CORE/BODY/EDGE by distance from edge). Replaced by **structural tiers** (Tier C = smooth Gaussian aesthetic field, Tier A/B = catastrophe germs carrying payload). See `03_PHOXOIDAL_CARRIER_ARCHITECTURE.md` §3.

`02_FAILURE_MODEL_ANALYSIS.md` argues why this transition is the right move; `04_DIFFEOMORPHISM_INVARIANCE_ARGUMENT.md` argues that the math supports the new substrate's robustness claim; `08_HONEST_TRADEOFFS.md` argues what the costs are.

---

**Reviewer checklist.** If this digest is wrong on any of: (a) the constants in §2, (b) the manifest layout in §4, (c) the tier-assignment rule in §5, (d) the parity scheme in §8.1, (e) the CRC-link scheme in §8.2, (f) the inner header in §9, or (g) the load-bearing-function inventory in §12, the proposal that depends on this digest is wrong. The cited line numbers point at the live source; verify the ones that matter to you.
