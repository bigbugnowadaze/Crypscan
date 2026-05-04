"""Test spike-9B substrate under various channel severities.

Establishes the operating envelope of the channel-matched substrate.
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


def run(label: str, params: ChannelParams) -> dict:
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        clean = td / 'c.png'
        encoder.encode(PAYLOAD, 'spike9b.txt', clean)
        arr = np.asarray(Image.open(clean).convert('L'), dtype=np.float32) / 255.0
        distorted = apply_screen_camera_channel(arr, params)
        d = td / 'd.png'
        Image.fromarray((distorted * 255 + 0.5).astype(np.uint8), mode='L').save(d)
        res = decoder.decode(d, use_per_quadrant_calibration=True)
        return {
            'label': label, 'pass': res.sha256_ok,
            'pose_ok': res.pose_ok,
            'ncc': res.median_payload_ncc,
            'rs_corr': res.rs_corrected_frames,
            'rs_fail': len(res.rs_failed_frames),
            'err': res.decode_error,
        }


def main():
    # Sweep across JPEG quality, perspective tilt, gaussian noise
    tests = [
        ("baseline (default)", ChannelParams()),
        ("JPEG q=95", ChannelParams(jpeg_quality=95)),
        ("JPEG q=70", ChannelParams(jpeg_quality=70)),
        ("JPEG q=50", ChannelParams(jpeg_quality=50)),
        ("JPEG q=30", ChannelParams(jpeg_quality=30)),
        ("perspective_tilt=0", ChannelParams(perspective_tilt_deg=0)),
        ("perspective_tilt=10", ChannelParams(perspective_tilt_deg=10)),
        ("perspective_tilt=20", ChannelParams(perspective_tilt_deg=20)),
        ("perspective_tilt=30", ChannelParams(perspective_tilt_deg=30)),
        ("gaussian σ=0.005", ChannelParams(gaussian_sigma=0.005)),
        ("gaussian σ=0.02", ChannelParams(gaussian_sigma=0.02)),
        ("gaussian σ=0.05", ChannelParams(gaussian_sigma=0.05)),
        ("gaussian σ=0.10", ChannelParams(gaussian_sigma=0.10)),
        ("camera oversample=1.0", ChannelParams(camera_oversample=1.0)),
        ("camera oversample=3.0", ChannelParams(camera_oversample=3.0)),
        ("subpixel + 30° tilt + JPEG 50 (severe)",
         ChannelParams(jpeg_quality=50, perspective_tilt_deg=30,
                          gaussian_sigma=0.05)),
    ]
    print(f"{'CONFIG':<48} {'PASS':<6} {'NCC':<6} {'RS_CORR':<8} {'NOTES'}")
    print('-' * 100)
    for label, p in tests:
        r = run(label, p)
        sym = 'PASS' if r['pass'] else 'FAIL'
        notes = r['err'] or ''
        print(f"  {label:<46} {sym:<6} {r['ncc']:.3f}  {r['rs_corr']:>2}/{r['rs_fail']:<3}  {notes[:50]}")


if __name__ == '__main__':
    main()
