"""Generate the spike-8B reference carrier (P3.A substrate).

Run ONCE to produce `reference_carrier.png` + `reference_carrier.info.json`.
The carrier is committed to the repo so the partnership has a single,
deterministic file to display on each screen during capture.

Why P3.A and not P3.B:
    Spike-8B validates the PRODUCTION substrate. P3.A is what V1 ships.
    P3.B real-camera validation is a follow-up (spike-8B-supplemental
    can be authorized later if envelope-parity work proceeds).

Reference payload:
    A short, recognizable string with a known SHA-256. When the decoder
    succeeds on a capture, the partnership sees the literal string in
    the report and knows the round-trip worked.
"""
from __future__ import annotations
import hashlib
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
P3A = HERE.parent / 'p3a_aruco'
sys.path.insert(0, str(P3A))

from encoder import encode, EncodeParams                          # noqa: E402


REFERENCE_PAYLOAD = (
    b"SPIKE-8B real-camera validation reference carrier.\n"
    b"P3.A substrate (ArUco DICT_4X4_50 corners + spike-7 codebook).\n"
    b"Authored 2026-05-04 on branch claude/phase-0-v5-handoff-Sx50S.\n"
    b"If you're reading this from a decoded phone capture, the round-trip "
    b"survived display + camera + JPEG. That's the win condition.\n"
)
REFERENCE_FILENAME = "spike8b_reference.txt"


def main() -> int:
    out_png = HERE / 'reference_carrier.png'
    out_info = HERE / 'reference_carrier.info.json'

    info = encode(
        REFERENCE_PAYLOAD, REFERENCE_FILENAME, out_png,
        params=EncodeParams(pixel_bit_depth=8),
        sidecar=False,
    )

    expected_sha = hashlib.sha256(REFERENCE_PAYLOAD).hexdigest()
    augmented = {
        **info,
        'reference_payload_text': REFERENCE_PAYLOAD.decode('utf-8'),
        'reference_payload_size': len(REFERENCE_PAYLOAD),
        'reference_payload_sha256': expected_sha,
        'reference_carrier_purpose': (
            "spike-8B real-camera validation. Display this PNG full-screen "
            "on each test screen and capture with each test phone per "
            "CAPTURE_PROTOCOL.md."
        ),
    }
    out_info.write_text(json.dumps(augmented, indent=2))

    print(f"Reference carrier written to {out_png.relative_to(HERE.parent.parent)}")
    print(f"  PNG bytes:    {info['png_bytes']:,}")
    print(f"  Canvas:       {info['canvas']}")
    print(f"  Payload SHA:  {expected_sha}")
    print(f"  Info JSON:    {out_info.relative_to(HERE.parent.parent)}")
    return 0


if __name__ == '__main__':
    sys.exit(main())
