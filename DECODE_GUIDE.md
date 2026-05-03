# Aurexis E/D — Decoder Guide

## What this is

A standalone Python decoder for Aurexis AXP6 PNGs. If Vince encodes a file using the Aurexis encoder, you can decode that PNG back to the exact original file using this tool. Same bytes, same SHA-256 hash — verified automatically.

## What you need

1. **Python 3.6+** (you probably already have it)
2. **The brotli Python module** (one install command)
3. **aurexis_decode.py** (this file — that's it, single file)

## Setup (one time)

Open a terminal and run:

```bash
pip install brotli
```

That's it. No other dependencies needed. Everything else is Python standard library.

To verify it's ready:

```bash
python aurexis_decode.py --help
```

You should see the help text and `brotli module: INSTALLED (ready)`.

## How to decode a file

Vince sends you a PNG file (e.g. `report.json.axp6.png`). To decode it:

```bash
python aurexis_decode.py report.json.axp6.png
```

This outputs the original file to the same directory as the PNG. The decoder automatically:
- Reads the AXP6 carrier format from the PNG
- Verifies parity (error detection)
- Verifies integrity (neighborhood-linked CRC-8 per block)
- Decompresses (Brotli)
- Verifies SHA-256 hash matches the original
- Writes the original file with its original filename

### Decode to a specific folder

```bash
python aurexis_decode.py report.json.axp6.png -o decoded/
```

### Just see what's in a PNG without decoding

```bash
python aurexis_decode.py report.json.axp6.png --info
```

Shows filename, sizes, compression ratio, SHA-256 hash, verification status.

## What a successful decode looks like

```
╔══════════════════════════════════════════════════════════╗
║         Aurexis E/D — AXP6 Decoder (Python)            ║
╚══════════════════════════════════════════════════════════╝

  Input:       report.json.axp6.png (79.9 KB)
  Output:      report.json (500.0 KB)
  Compression: brotli
  Ratio:       16.0% (PNG was 16.0% of original)

  SHA-256:     a1b2c3d4...full 64-char hash...
  Verified:    YES — byte-exact match
  Parity:      VERIFIED
  Integrity:   VERIFIED

  Saved to:    decoded/report.json

══════════════════════════════════════════════════════════
  DECODE COMPLETE — file restored, SHA-256 verified
══════════════════════════════════════════════════════════
```

If you see `DECODE COMPLETE — file restored, SHA-256 verified`, the file is an exact byte-for-byte copy of what Vince encoded. Guaranteed.

## What counts as proof

For the decode to be a valid proof of the encode/decode pathway:

1. **SHA-256 Verified = YES** — the decoded file has the exact same hash as the original
2. **Parity = VERIFIED** — the XOR parity blocks in the PNG are intact
3. **Integrity = VERIFIED** — all data blocks pass neighborhood-linked CRC-8 check

If any of these fail, the decoder will tell you exactly what went wrong.

## Troubleshooting

**"This file was compressed with Brotli. Install it with: pip install brotli"**
Run `pip install brotli` and try again.

**"Not a valid PNG file"**
The file isn't a PNG. Make sure you got the right file from Vince.

**"Not an AXP6 carrier"**
The PNG exists but isn't an Aurexis-encoded file. It's just a regular PNG.

**"SHA-256 MISMATCH"**
The decoded data doesn't match the original. The file may have been corrupted in transit. Ask Vince to re-send.

**"Integrity check failed: N blocks corrupted"**
Some data blocks in the PNG are damaged. If only a few blocks, the parity system might have recovered them (in the Node decoder). This Python decoder doesn't do recovery — it reports the error.

## File types that work

The encoder handles any file, but these classes compress well:

| Type | Typical compression |
|---|---|
| Text (.txt, .md) | 5-24% of original |
| JSON (.json) | 12-17% |
| Source code (.js, .py) | 3-11% |
| Log files (.log) | 10-13% |
| CSV (.csv) | 25-36% |

Random/encrypted/pre-compressed files will be larger as PNGs (that's mathematically correct — no lossless codec can compress everything).
