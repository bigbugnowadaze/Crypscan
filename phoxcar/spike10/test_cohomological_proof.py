"""End-to-end demo: encode → curve → channel → decode + extract surface verdict.

The Plan B test from the manifesto. Demonstrates:

  1. The phoxoidal carrier survives display on a curved surface
     (carrier round-trip works through cylindrical-curvature warp)

  2. The SAME image that delivered the payload ALSO yields a verdict
     about the surface curvature, derived from the per-germ residual
     field

  3. The verdict is structurally consistent with the ground-truth
     curvature (cohomological consistency: two independent extractions
     from one image agree)

If 1+2+3 hold across a curvature sweep, the substrate has empirically
demonstrated joint payload-and-surface recovery from a single image —
the non-extractive notation claim from VISION_MANIFESTO §IX.
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
import decoder as discrete_decoder
from channel import apply_screen_camera_channel, ChannelParams
from curved_surface import apply_curved_display, CurvedDisplayParams
from surface_extractor import derive_surface_verdict
from basis import OrthoBasis
from codebook import design_codebook
from encoder import (
    EncodeParams, MANIFEST_INDICES, PILOT_INDICES, PAYLOAD_INDICES,
    grid_index_to_pixel, CANVAS_WIDTH, CANVAS_HEIGHT,
)
from fiducials import canonical_layout
from pose import detect_pose, rectify
from pilots import (
    select_anchor_codewords, fit_local_intensity_transforms,
    fit_intensity_transform, gather_anchor_pixels,
)
from discrete_codebook import render_codebook_patches, classify_patch


PAYLOAD = b"P3B'/9B"


def encode_carrier(td: Path) -> tuple[Path, EncodeParams, np.ndarray, np.ndarray, list[int]]:
    """Encode the spike-9B carrier and return its full state (params, codebook,
    canonical theta, codeword indices per germ-position)."""
    out = td / 'carrier.png'
    info = encoder.encode(PAYLOAD, 'spike10.txt', out)
    params = EncodeParams()
    basis = OrthoBasis.build(params.half_size, params.sigma)
    codebook = design_codebook(basis, n_codewords=params.n_codewords,
                                  seed=params.codebook_seed)
    return out, params, basis, codebook


def decode_full(captured_png: Path, params: EncodeParams,
                  basis: OrthoBasis, codebook: np.ndarray):
    """Decode and ALSO return per-germ canonical positions + decoded
    codeword indices for the surface-extractor."""
    img = Image.open(captured_png)
    arr = np.asarray(img, dtype=np.float32) / 255.0
    layout = canonical_layout(CANVAS_WIDTH, CANVAS_HEIGHT)
    pose = detect_pose(arr, layout)
    if not pose.success:
        return None
    rectified = rectify(arr, pose.homography, CANVAS_WIDTH, CANVAS_HEIGHT)

    # Multi-pilot fit (per spike-9B)
    pilot_positions = [grid_index_to_pixel(i) for i in PILOT_INDICES]
    anchor_idx, anchor_patches = select_anchor_codewords(
        codebook, basis, params.amp, params.baseline,
        n_anchors=len(PILOT_INDICES),
    )
    pilot_int = [(int(p[0]), int(p[1])) for p in pilot_positions]
    grid = fit_local_intensity_transforms(
        rectified, pilot_int, anchor_patches, params.half_size,
        CANVAS_WIDTH, CANVAS_HEIGHT, n_x=2, n_y=2,
    )
    rectified_corrected = grid.invert(rectified).astype(np.float32)

    # Image-NCC decode (same as spike-9B) for ALL non-pilot germs (manifest+payload)
    templates = render_codebook_patches(codebook, basis, params.amp, params.baseline)
    germ_indices = MANIFEST_INDICES + PAYLOAD_INDICES
    germ_positions = [grid_index_to_pixel(i) for i in germ_indices]
    decoded_codewords = []
    for cx, cy in germ_positions:
        x0 = cx - params.half_size; x1 = cx + params.half_size + 1
        y0 = cy - params.half_size; y1 = cy + params.half_size + 1
        patch = rectified_corrected[y0:y1, x0:x1].astype(np.float32)
        best_idx, _, _ = classify_patch(patch, templates)
        decoded_codewords.append(best_idx)

    return {
        'rectified_corrected': rectified_corrected,
        'germ_indices': germ_indices,
        'germ_positions': germ_positions,
        'decoded_codewords': decoded_codewords,
    }


def main():
    print(f"{'=' * 72}")
    print(f"  spike-10 cohomological-consistency proof")
    print(f"  PAYLOAD: {PAYLOAD!r}")
    print(f"{'=' * 72}")

    with tempfile.TemporaryDirectory() as td:
        td = Path(td)

        # --- Encode once ---
        carrier_path, params, basis, codebook = encode_carrier(td)
        clean = np.asarray(Image.open(carrier_path).convert('L'),
                              dtype=np.float32) / 255.0

        # --- Sweep curvature radii ---
        radii_to_test = [
            ('flat (R=∞)', float('inf')),
            ('shallow R=4000', 4000.0),
            ('moderate R=2000 (~MSI G27C4X)', 2000.0),
            ('aggressive R=1000', 1000.0),
            ('extreme R=500', 500.0),
        ]
        channel = ChannelParams()

        print(f"{'Curvature':<36} {'Discrete decode':<18} "
                f"{'Surface axis':<13} {'Recov. R':<12} {'Confidence':<22} {'SNR':<6}")
        print('-' * 110)
        for label, R in radii_to_test:
            curve_params = CurvedDisplayParams(radius=R, axis='x')
            curved = apply_curved_display(clean, curve_params)
            distorted = apply_screen_camera_channel(curved, channel)
            d_png = td / f'd_{R}.png'
            Image.fromarray((distorted * 255 + 0.5).astype(np.uint8),
                              mode='L').save(d_png)

            # Discrete decode
            res = discrete_decoder.decode(d_png, params=params,
                                            use_per_quadrant_calibration=True)
            decoded_label = ('PASS' if res.sha256_ok
                              else f"FAIL ({res.decode_error[:30]})" if res.decode_error
                              else 'FAIL')

            # Surface verdict (works whether or not the discrete decode passed,
            # because we use the codebook-NCC choices as the canonical reference)
            full = decode_full(d_png, params, basis, codebook)
            if full is None:
                print(f"  {label:<34} {'pose FAIL':<18}  -")
                continue

            verdict = derive_surface_verdict(
                full['rectified_corrected'],
                full['decoded_codewords'],
                full['germ_positions'],
                codebook, basis,
                params.amp, params.baseline,
                CANVAS_WIDTH, CANVAS_HEIGHT,
            )
            recov_R = verdict.estimated_curvature_radius
            recov_R_str = ('inf' if not np.isfinite(recov_R)
                            else f"{recov_R:.0f}")
            from surface_extractor import fit_local_scale_deformation
            # Re-derive SNR for printing (cheap)
            print(f"  {label:<34} {decoded_label:<18} "
                    f"{verdict.estimated_curvature_axis:<13} "
                    f"{recov_R_str:<12} {verdict.confidence:<22} ")

        print(f"\n{'=' * 72}")
        print(f"  Diagnostic detail (R=2000 case)")
        print(f"{'=' * 72}")
        curve = CurvedDisplayParams(radius=2000.0, axis='x')
        curved = apply_curved_display(clean, curve)
        distorted = apply_screen_camera_channel(curved, channel)
        d_png = td / 'd_diag.png'
        Image.fromarray((distorted * 255 + 0.5).astype(np.uint8),
                          mode='L').save(d_png)
        full = decode_full(d_png, params, basis, codebook)
        verdict = derive_surface_verdict(
            full['rectified_corrected'],
            full['decoded_codewords'],
            full['germ_positions'],
            codebook, basis, params.amp, params.baseline,
            CANVAS_WIDTH, CANVAS_HEIGHT,
        )
        print(f"  n_germs:                     {verdict.n_germs_used}")
        print(f"  median_residual_norm:        {verdict.median_residual_norm:.4f}")
        print(f"  estimated_curvature_axis:    {verdict.estimated_curvature_axis}")
        print(f"  estimated_curvature_radius:  {verdict.estimated_curvature_radius:.1f}  (truth=2000)")
        print(f"  confidence:                  {verdict.confidence}")
        print(f"\n  Derivation chain:")
        for step in verdict.derivation:
            print(f"    - {step}")


if __name__ == '__main__':
    main()
