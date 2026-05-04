"""Generate the spike-9B reference carrier (channel-matched substrate).

Writes `reference_carrier_v9b.png` + `.info.json` containing the encode
parameters and expected payload SHA-256.

Run ONCE; the resulting carrier is committed to the repo so the partnership
can display + capture it deterministically.
"""
from __future__ import annotations
import hashlib
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import encoder
from encoder import EncodeParams


REFERENCE_PAYLOAD = (
    b"SPIKE-9B (P3.B-prime) channel-matched catastrophe-germ carrier. "
    b"sigma=8 + image-NCC + multi-pilot. If decoded from a real phone "
    b"capture, the analytic substrate survives screen-camera. Win condition."
)
REFERENCE_FILENAME = "spike9c_reference.txt"


def main() -> int:
    out_png = HERE / 'reference_carrier_v9b.png'
    out_info = HERE / 'reference_carrier_v9b.info.json'

    # NOTE: the reference payload above (~199 bytes) won't fit in the
    # spike-9B canvas (capacity = ~145 bytes raw, ~60 bytes useful post
    # RS+AXP6+Brotli). Use a tiny payload that fits the channel-existence
    # test.
    short_payload = b"P3B'/9B"
    print(f"  short payload: {short_payload!r} ({len(short_payload)} bytes)")
    info = encoder.encode(
        short_payload, REFERENCE_FILENAME, out_png, params=EncodeParams(),
    )
    expected_sha = hashlib.sha256(short_payload).hexdigest()
    info['reference_payload_text'] = short_payload.decode('utf-8',
                                                              errors='replace')
    info['reference_payload_size'] = len(short_payload)
    info['reference_payload_sha256'] = expected_sha
    info['reference_carrier_purpose'] = (
        "spike-9C real-camera validation of the channel-matched "
        "catastrophe-germ substrate. Display this PNG fullscreen "
        "(F11 in Chrome at native 1:1) on the chosen test screen "
        "and capture per the existing spike-8B CAPTURE_PROTOCOL.md."
    )
    out_info.write_text(json.dumps(info, indent=2))

    print(f"\nReference carrier written to "
            f"{out_png.relative_to(HERE.parent.parent)}")
    print(f"  PNG bytes:   {info['png_bytes']:,}")
    print(f"  Canvas:      {info['canvas']}")
    print(f"  Germ grid:   {info['germ_grid']}")
    print(f"  Payload SHA: {expected_sha}")
    print(f"  Info JSON:   {out_info.relative_to(HERE.parent.parent)}")
    return 0


if __name__ == '__main__':
    sys.exit(main())
