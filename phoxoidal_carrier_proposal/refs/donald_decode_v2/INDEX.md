# refs/donald_decode_v2/

The standalone AXP6 decoder bundle (`donald_decode_v2.zip` per the v4 handoff §"Local files"). Contents extracted into the root of this Crypscan repo.

| File | Status | What the proposal cites it for |
|---|---|---|
| `aurexis_decode.py` | ✓ Present at `/home/user/Crypscan/aurexis_decode.py` (737 lines) | The source-of-truth for `01_AXP6_ARCHITECTURE_DIGEST.md`. Every line citation in §1–§12 of that doc points here. |
| `DECODE_GUIDE.md` | ✓ Present at `/home/user/Crypscan/DECODE_GUIDE.md` | User-facing decoder manual. Cited in `02_FAILURE_MODEL_ANALYSIS.md` §1.5 (deployment shape) and §2 (the "Vince sends you a PNG file" line). |
| `sample-2.mp4.axp6.png` | ✓ Available as a GitHub Release asset on this repo (verified 2026-05-03) | The 30 MB video encoded as an 11032×13120 PNG (PNG-on-disk size 36,203,687 bytes; bit_depth 2; color_type 3). Direct download: `https://github.com/bigbugnowadaze/Crypscan/releases/download/png/sample-2.mp4.axp6.png`. Demonstration artifact; not required for Phase 0. See `ADDENDUM_01_img2phox_integration.md` §7 for the verification details. |

## On the sample carrier PNG (updated 2026-05-03)

The user uploaded the sample carrier as a GitHub Release asset on this repo (release tag `png`, asset name `sample-2.mp4.axp6.png`). It is now reachable at:

```
https://github.com/bigbugnowadaze/Crypscan/releases/download/png/sample-2.mp4.axp6.png
```

Verified during the addendum pass (`ADDENDUM_01_img2phox_integration.md` §7):

- File size: 36,203,687 bytes.
- PNG signature: OK.
- IHDR: width=11032, height=13120, bit_depth=2, color_type=3 — matches `aurexis_decode.py` line 84 expectations and `05_INFORMATION_DENSITY_ANALYSIS.md` §1's stated dimensions.

Phase 0 did not load this PNG (Phase 0 is proposal authoring, not roundtrip verification — the architecture digest in `01_AXP6_ARCHITECTURE_DIGEST.md` is sourced from `aurexis_decode.py`'s source code). For Phase 1 it is a non-blocking dependency: download via `curl` from the release URL above and treat as a fixture.

## On the inner decoder details

`aurexis_decode.py` line citations the proposal relies on, in proposal-document order:

| Doc | Lines |
|---|---|
| `01_AXP6_ARCHITECTURE_DIGEST.md` §2 | 39–52 (constants), 195–217 (modules ↔ bytes) |
| §3 | 57–138 (`read_indexed_png`), 141–177 (`_decode_png_full`), 180–190 (`_paeth`) |
| §4 | 272–330 (`read_manifest`) |
| §5 | 222–255 (`assign_tiers`), 427–432 (manifest tier-count check) |
| §6 | 335–353 (`extract_tier_blocks`), 437–445 (partition logic) |
| §7 | 260–267 (`tier_deinterleave`) |
| §8.1 | 452–493 (parity verification driver), 617–635 (`_compute_tier_parity`) |
| §8.2 | 358–367 (`_build_crc8_table`), 369–376 (`crc8_linked`), 379–399 (`compute_linked_crcs`), 496–509 (CRC layout) |
| §9 | 526–532 (payload reassembly), 535–548 (inner header parse) |
| §10 | 567–585 (decompression + SHA-256 verify) |
| §12 | inventory of pixel-grid-dependent functions across the file |

If any of these cites a line range that is wrong, the digest is wrong and the proposal is wrong. The reviewer should spot-check at least: the constants block (§2), `assign_tiers` (§5), and the inner-header layout (§9), which are the load-bearing claims.
