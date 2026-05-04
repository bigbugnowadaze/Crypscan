"""Spike-9B test on the spike-9A synthetic channel.

Encodes a small payload with the channel-matched-scale + multi-pilot
substrate, pushes through the channel that reproduced spike-8B run 4
failure, decodes. Pass = SHA-256 round-trip ok.

Compare against:
  - V0 control (P3.A as-is) — already known to fail this channel
  - V_scale only (σ=8 + image-space NCC, single global pilot fit)
  - V_full (σ=8 + image-space NCC + per-quadrant pilot fit) — the hypothesis
"""
from __future__ import annotations
import sys
import tempfile
from pathlib import Path

import numpy as np
from PIL import Image

import encoder
import decoder
from channel import apply_screen_camera_channel, ChannelParams


PAYLOAD = b"P3B'/9B"


def run_one(label: str, use_per_quadrant: bool, channel_params: ChannelParams):
    print(f"\n{'=' * 70}")
    print(f"  {label}")
    print(f"{'=' * 70}")
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        clean_png = td / 'clean.png'
        info = encoder.encode(PAYLOAD, 'spike9b.txt', clean_png)
        clean_arr = np.asarray(Image.open(clean_png).convert('L'),
                                  dtype=np.float32) / 255.0
        distorted = apply_screen_camera_channel(clean_arr, channel_params)
        d_png = td / 'd.png'
        Image.fromarray((distorted * 255 + 0.5).astype(np.uint8),
                          mode='L').save(d_png)
        res = decoder.decode(d_png, use_per_quadrant_calibration=use_per_quadrant)
        print(f"  pose_ok:                 {res.pose_ok}")
        print(f"  sha_ok:                  {res.sha256_ok}")
        print(f"  decode_error:            {res.decode_error}")
        print(f"  pilot_calibration:       {res.pilot_calibration}")
        print(f"  n_pilots_per_quadrant:   {res.n_pilots_per_quadrant}")
        print(f"  median_manifest_ncc:     {res.median_manifest_ncc:.3f}")
        print(f"  median_payload_ncc:      {res.median_payload_ncc:.3f}")
        print(f"  rs_corrected_frames:     {res.rs_corrected_frames}")
        if res.rs_failed_frames:
            print(f"  rs_failed_frames:        {res.rs_failed_frames}")
        return res


def main():
    print(f"Testing spike-9B substrate on the calibrated synthetic channel.")
    print(f"  Payload: {PAYLOAD!r} ({len(PAYLOAD)} bytes)")

    # Channel: same as spike-9A's "default" config (reproduces spike-8B run 4)
    default_channel = ChannelParams()
    no_subpixel_channel = ChannelParams(subpixel_pattern='none')

    results = {}
    results['no-subpixel (sanity)'] = run_one(
        "Sanity: no subpixel raster channel (should pass cleanly)",
        use_per_quadrant=True, channel_params=no_subpixel_channel,
    )
    results['σ=8 + global pilot'] = run_one(
        "V_scale: σ=8 channel-matched + GLOBAL pilot fit + image-space NCC",
        use_per_quadrant=False, channel_params=default_channel,
    )
    results['σ=8 + per-quadrant pilot'] = run_one(
        "V_full: σ=8 channel-matched + PER-QUADRANT pilot fit + image-space NCC",
        use_per_quadrant=True, channel_params=default_channel,
    )

    print(f"\n{'=' * 70}")
    print(f"  Summary")
    print(f"{'=' * 70}")
    for label, res in results.items():
        sym = 'PASS' if res.sha256_ok else 'FAIL'
        print(f"  [{sym}] {label}: median_ncc={res.median_payload_ncc:.3f} "
                f"rs_corr={res.rs_corrected_frames}")


if __name__ == '__main__':
    main()
