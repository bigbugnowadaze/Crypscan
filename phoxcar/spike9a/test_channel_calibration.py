"""Calibrate the synthetic channel against the spike-8B run 4 failure mode.

Goal: verify that running an encoded P3.A carrier through `channel.py` and
then decoding produces the SAME failure mode (manifest magic mismatch,
codebook NN returning wrong bytes) as the real-capture failure on the Asus
laptop.

If yes -> we have a closed-loop test bed and can iterate substrate variants
against it.

If no -> the channel doesn't model the right distortion; need to revisit it.

Run:
    python3 test_channel_calibration.py
"""
from __future__ import annotations
import sys
import tempfile
from pathlib import Path

import numpy as np
from PIL import Image

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import encoder
import decoder
from channel import apply_screen_camera_channel, ChannelParams


PAYLOAD = (
    b"SPIKE-9A synthetic channel calibration. "
    b"If this round-trips, the channel is too gentle. "
    b"If it fails with manifest magic mismatch, the channel reproduces "
    b"the spike-8B run 4 failure mode."
)


def main():
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        clean_png = td / 'clean_carrier.png'
        info = encoder.encode(PAYLOAD, 'spike9a_calibration.txt', clean_png)
        print(f"Encoded carrier: {info['canvas']}, {info['png_bytes']} bytes")

        # Sanity: decode the clean carrier (zero-warp) — should pass
        clean_res = decoder.decode(clean_png)
        print(f"\nClean carrier decode (sanity): {'PASS' if clean_res.sha256_ok else 'FAIL'}")
        if not clean_res.sha256_ok:
            print(f"  decode_error: {clean_res.decode_error}")
            print("  ABORT: encoder/decoder broken before applying any channel")
            return 1

        # Apply the channel
        clean_arr = np.asarray(Image.open(clean_png).convert('L'), dtype=np.float32) / 255.0
        for label, params in [
            ("default channel", ChannelParams()),
            ("low-distortion channel", ChannelParams(jpeg_quality=95,
                                                       perspective_tilt_deg=2.0,
                                                       gaussian_sigma=0.005,
                                                       camera_oversample=1.0)),
            ("high-distortion channel", ChannelParams(jpeg_quality=70,
                                                        perspective_tilt_deg=8.0,
                                                        gaussian_sigma=0.03,
                                                        camera_oversample=2.5)),
            ("no subpixel raster", ChannelParams(subpixel_pattern='none')),
        ]:
            distorted = apply_screen_camera_channel(clean_arr, params)
            distorted_png = td / f"channel_{label.replace(' ', '_')}.png"
            Image.fromarray((distorted * 255 + 0.5).astype(np.uint8), mode='L').save(distorted_png)
            res = decoder.decode(distorted_png)
            print(f"\n{label}:")
            print(f"  pose_ok:       {res.pose_ok}")
            print(f"  sha_ok:        {res.sha256_ok}")
            print(f"  decode_error:  {res.decode_error}")
            if res.transform:
                print(f"  pilot fit:     a={res.transform.a:+.3f} b={res.transform.b:+.3f} γ={res.transform.gamma:.3f}")
            # Save the distorted image for inspection
            outdir = HERE / 'results'
            outdir.mkdir(parents=True, exist_ok=True)
            (outdir / f'channel_{label.replace(" ", "_").replace("-", "_")}.png').write_bytes(
                distorted_png.read_bytes())

        print(f"\nCalibration target: real spike-8B run 4 reported "
                f"'manifest parse failed: manifest magic mismatch'")
        print(f"  - if at least one channel config reproduces that, the harness is calibrated")
        print(f"  - if all configs PASS, channel is too gentle (need more distortion)")
        print(f"  - if all FAIL on pose, channel is too aggressive (need less)")
    return 0


if __name__ == '__main__':
    sys.exit(main())
