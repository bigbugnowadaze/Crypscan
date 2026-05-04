"""P3.B zero-warp smoke test.

If this passes, the phoxoidal-native pose recovery architecture is
empirically validated end-to-end. From there we extend to the full
photometric + geometric sweep.
"""
from __future__ import annotations
import json
import sys
import tempfile
from pathlib import Path

import numpy as np
from PIL import Image

import encoder
import decoder
from fiducials import canonical_layout
from pose import detect_pose
from basis import OrthoBasis


PAYLOAD = b"P3.B phoxoidal-native pose: catastrophe-germ matched-filter NCC detection. " \
            b"This is a research path to retire the ArUco dependency in P3.A. " \
            b"If this decodes, the substrate is fully thesis-aligned end-to-end."
FILENAME = "p3b_smoke.txt"


def main():
    with tempfile.TemporaryDirectory() as td:
        png = Path(td) / "p3b_smoke.png"
        info = encoder.encode(PAYLOAD, FILENAME, png, sidecar=False)
        print(f"--- encode ---")
        print(json.dumps({k: v for k, v in info.items()
                            if k not in ('params', 'anchor_codeword_indices')},
                          indent=2))

        # Sanity: detect pose on the un-warped encoded image (should be trivial)
        captured = np.asarray(Image.open(png).convert('L')).astype(np.float32) / 255.0
        params = encoder.EncodeParams()
        basis = OrthoBasis.build(params.half_size, params.sigma)
        layout = canonical_layout(encoder.CANVAS_WIDTH, encoder.CANVAS_HEIGHT,
                                    half_size=params.half_size)
        pose = detect_pose(captured, basis, layout)
        print(f"--- pose detection ---")
        for d in pose.detections:
            print(f"  {d.name}: NCC={d.peak_score:.4f} scale={d.best_scale} xy={d.peak_xy}")
        if not pose.success:
            print(f"  POSE FAILED: {pose.error}")
            sys.exit(1)

        res = decoder.decode(png)
        print(f"--- decode ---")
        print(json.dumps(res.summary(), indent=2))
        ok = (res.sha256_ok and res.size_ok and res.payload == PAYLOAD
                and res.filename == FILENAME)
        print(f"\nZERO-WARP GATE: {'PASS' if ok else 'FAIL'}")
        sys.exit(0 if ok else 1)


if __name__ == '__main__':
    main()
