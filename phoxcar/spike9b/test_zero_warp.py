"""Spike-9B zero-warp sanity test."""
from __future__ import annotations
import json
import sys
import tempfile
from pathlib import Path

import numpy as np
from PIL import Image

import encoder
import decoder

PAYLOAD = b"P3B'/9B"

with tempfile.TemporaryDirectory() as td:
    td = Path(td)
    png = td / 'spike9b.png'
    info = encoder.encode(PAYLOAD, 'spike9b.txt', png)
    print(f"--- encode ---")
    print(json.dumps({k: v for k, v in info.items()
                        if k not in ('params', 'anchor_codeword_indices',
                                       'pilot_indices', 'manifest_indices')},
                      indent=2))
    res = decoder.decode(png)
    print(f"--- decode ---")
    print(f"  pose_ok:                {res.pose_ok}")
    print(f"  sha_ok:                 {res.sha256_ok}")
    print(f"  pilot_calibration:      {res.pilot_calibration}")
    print(f"  n_pilots_per_quadrant:  {res.n_pilots_per_quadrant}")
    print(f"  median_manifest_ncc:    {res.median_manifest_ncc:.3f}")
    print(f"  median_payload_ncc:     {res.median_payload_ncc:.3f}")
    print(f"  rs_corrected_frames:    {res.rs_corrected_frames}")
    if res.decode_error:
        print(f"  decode_error:           {res.decode_error}")
    print(f"  ZERO-WARP GATE: {'PASS' if res.sha256_ok else 'FAIL'}")
    sys.exit(0 if res.sha256_ok else 1)
