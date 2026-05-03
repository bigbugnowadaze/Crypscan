"""End-to-end phoxcar spike ENCODER.

Pipeline:
    payload bytes
        -> Brotli compress
        -> AXP6-equivalent inner header (header.pack_header)
        -> pad to germ boundary
        -> bytes -> 5-coef germs (germ_codec.bytes_to_germs)
        -> place at known scene positions on a regular grid
        -> render to 2D carrier (render.render_carrier)
        -> save as lossless 8-bit grayscale PNG
"""
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
import json

import brotli
import numpy as np
from PIL import Image

from header import pack_header
from germ_codec import (
    bytes_to_germs, germs_to_bytes, n_germs_for_bytes, pad_bytes_to_germ_boundary,
    quantize_then_dequantize, BYTES_PER_GERM,
)
from render import render_carrier, make_grid_positions


@dataclass
class EncodeParams:
    """Spike-specific render + grid parameters. Encoder/decoder share these.

    The 16-bit PNG depth is an empirical finding from the spike: at 8-bit
    pixel depth, the per-coefficient inverse-fit error exceeds half a
    quantization step on the kappa terms (which are weakly identified
    relative to the Gaussian envelope's correlation with the s^2 / t^2
    basis). Production substrate can either use 16-bit pixel depth, an
    orthogonalized germ basis, or a smaller bit count per coefficient —
    this question is `09_OPEN_QUESTIONS.md` section 6 territory.
    """
    sigma: float = 4.0           # local Mahalanobis envelope, in pixels
    half_size: int = 12          # patch half-window in pixels (so patch is 25x25)
    amp: float = 0.11            # H modulation amplitude
                                 # max envelope*sum(|basis|) over the patch is
                                 # 4.155, so amp <= 0.5/4.155 = 0.1203 keeps
                                 # every germ in the unit codebook strictly
                                 # within [0, 1] without any clipping
    baseline: float = 0.5        # background intensity in [0, 1]
    spacing: int = 28            # grid spacing in pixels (>= 2*half_size+1 = 25)
    margin: int = 24             # margin around grid
    pixel_bit_depth: int = 16    # 8 or 16 — 16-bit grayscale PNG is lossless and PIL-native

    def to_dict(self) -> dict:
        return {
            'sigma': self.sigma, 'half_size': self.half_size,
            'amp': self.amp, 'baseline': self.baseline,
            'spacing': self.spacing, 'margin': self.margin,
            'pixel_bit_depth': self.pixel_bit_depth,
        }


def encode(
    payload: bytes,
    filename: str,
    out_path: Path,
    params: EncodeParams | None = None,
    sidecar: bool = True,
) -> dict:
    """Encode payload bytes to a phoxcar PNG carrier.

    Args:
        payload: arbitrary bytes to encode.
        filename: stored in the AXP6 inner header for round-trip.
        out_path: PNG file to write.
        params: render + grid parameters (encoder/decoder must agree).
        sidecar: also write a `.json` next to the PNG with the manifest.
                 In Phase 1 this manifest will be encoded as a known-position
                 germ cluster in the carrier (`03_PHOXOIDAL_CARRIER_ARCHITECTURE.md`
                 section 7); the spike puts it on disk for simplicity.

    Returns:
        dict with encode statistics for logging.
    """
    if params is None:
        params = EncodeParams()
    out_path = Path(out_path)

    # 1. Brotli compress
    compressed = brotli.compress(payload, quality=11)

    # 2. AXP6 inner header
    framed = pack_header(payload, compressed, filename)
    n_framed = len(framed)

    # 3. Pad to germ boundary
    padded = pad_bytes_to_germ_boundary(framed)
    n_padded = len(padded)
    n_germs = n_padded // BYTES_PER_GERM

    # 4. Bytes -> germs (production-quantization-then-dequantization, so the
    #    encoder uses exactly the same dequantized values the decoder will
    #    recover from the bit stream).
    germs = quantize_then_dequantize(bytes_to_germs(padded, n_germs))

    # 5. Grid positions
    positions, width, height = make_grid_positions(
        n_germs, spacing=params.spacing, margin=params.margin,
    )

    # 6. Render
    canvas = render_carrier(
        germs, positions,
        width=width, height=height,
        sigma=params.sigma, half_size=params.half_size,
        amp=params.amp, baseline=params.baseline,
    )

    # 7. Save grayscale PNG (lossless). 16-bit by default per the spike's
    #    empirical finding; the format is a real PNG, just with higher pixel
    #    precision than AXP6's 2-bit indexed mode.
    out_path.parent.mkdir(parents=True, exist_ok=True)
    if params.pixel_bit_depth == 8:
        img = (np.clip(canvas, 0.0, 1.0) * 255.0 + 0.5).astype(np.uint8)
        Image.fromarray(img, mode='L').save(out_path, format='PNG')
    elif params.pixel_bit_depth == 16:
        img = (np.clip(canvas, 0.0, 1.0) * 65535.0 + 0.5).astype(np.uint16)
        Image.fromarray(img, mode='I;16').save(out_path, format='PNG')
    else:
        raise ValueError(f"unsupported pixel_bit_depth {params.pixel_bit_depth}")

    manifest = {
        'spike_version': '0.1',
        'filename': filename,
        'payload_size': len(payload),
        'compressed_size': len(compressed),
        'framed_size': n_framed,
        'padded_size': n_padded,
        'n_germs': n_germs,
        'width': width,
        'height': height,
        'params': params.to_dict(),
        'positions': positions.tolist(),
    }
    if sidecar:
        sidecar_path = out_path.with_suffix(out_path.suffix + '.manifest.json')
        sidecar_path.write_text(json.dumps(manifest, indent=2))
        manifest['sidecar_path'] = str(sidecar_path)
    manifest['png_path'] = str(out_path)
    manifest['png_bytes'] = out_path.stat().st_size
    return manifest


if __name__ == '__main__':
    import sys
    if len(sys.argv) < 3:
        print("usage: python encoder.py <input_file> <output_carrier.png>")
        sys.exit(1)
    in_path = Path(sys.argv[1])
    out_path = Path(sys.argv[2])
    payload = in_path.read_bytes()
    mf = encode(payload, in_path.name, out_path)
    print(json.dumps({k: v for k, v in mf.items() if k != 'positions'}, indent=2))
