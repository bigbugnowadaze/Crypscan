# refs/donald_decode_v2/

The standalone AXP6 decoder bundle (`donald_decode_v2.zip` per the v4 handoff §"Local files"). Contents extracted into the root of this Crypscan repo.

| File | Status | What the proposal cites it for |
|---|---|---|
| `aurexis_decode.py` | ✓ Present at `/home/user/Crypscan/aurexis_decode.py` (737 lines) | The source-of-truth for `01_AXP6_ARCHITECTURE_DIGEST.md`. Every line citation in §1–§12 of that doc points here. |
| `DECODE_GUIDE.md` | ✓ Present at `/home/user/Crypscan/DECODE_GUIDE.md` | User-facing decoder manual. Cited in `02_FAILURE_MODEL_ANALYSIS.md` §1.5 (deployment shape) and §2 (the "Vince sends you a PNG file" line). |
| `sample-2.mp4.axp6.png` | ⚠ Not loaded (Google Drive link only — see below) | The 30 MB video encoded as an 11032×13120 PNG. Demonstration artifact; not required for Phase 0. |

## On the sample carrier PNG

The handoff cites a 30 MB video encoded as an 11032×13120 carrier as a "proven working" demonstration artifact. The user noted this file is too large to upload to GitHub or to the Cowork uploads area and provided a Google Drive link.

**Phase 0 did not load this PNG.** The reasons:

1. Phase 0 is *proposal authoring*. The architecture digest in `01_AXP6_ARCHITECTURE_DIGEST.md` is sourced from the `aurexis_decode.py` source code, not from a roundtrip test of the sample carrier.
2. The carrier's stated dimensions (11032×13120 = 144,739,840 pixels) are honored verbatim wherever cited, e.g., in `05_INFORMATION_DENSITY_ANALYSIS.md` §1.
3. Loading the PNG via WebFetch from Google Drive is unreliable for files of this size and Drive's anti-scraping behavior may block automated downloads.

**For Phase 1**, if the partners want the sample carrier accessible to the development environment, recommended paths in order of preference:

1. **GitHub Release asset on this repo.** GitHub releases support assets up to 2 GB per file. Attach the 30 MB PNG as a release asset and reference its URL in this repo's README. This is the simplest path and gives a stable URL.
2. **`split -b 20m` then reassemble.** Split the PNG into ~20 MB chunks that fit GitHub's regular file size limit, commit them under `refs/donald_decode_v2/sample/`, and document the reassembly command in the INDEX. Keeps the artifact in-tree.
3. **Git LFS.** Standard git extension for large files; requires LFS configured on the repo.
4. **Direct upload to a stable URL not behind anti-scraping.** A self-hosted bucket, S3, etc. Less convenient than (1) but works.

None of these is required for Phase 0; all of them are reasonable for Phase 1.

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
