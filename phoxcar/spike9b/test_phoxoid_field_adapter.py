"""End-to-end test of the carrier-side phoxoid_field adapter.

  encode small payload via spike9b
  -> decode via spike9b
  -> wrap decode result as PhoxoidField via the adapter
  -> JSON-roundtrip the field
  -> validate
  -> compose with itself (sanity check that compose works on a real
     carrier-derived field)
"""
from __future__ import annotations
import sys
import tempfile
from pathlib import Path
import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import encoder
import decoder
from encoder import (
    EncodeParams, MANIFEST_INDICES, PILOT_INDICES, PAYLOAD_INDICES,
    grid_index_to_pixel, CANVAS_WIDTH, CANVAS_HEIGHT,
)
from fiducials import canonical_layout
from pose import detect_pose, rectify
from basis import OrthoBasis
from codebook import design_codebook
from pilots import (
    select_anchor_codewords, fit_local_intensity_transforms,
)
from discrete_codebook import render_codebook_patches, classify_patch

from phoxoid_field_adapter import carrier_decode_to_phoxoid_field
from phoxoid_field import (
    write_json, read_json, validate_field, compose_fields,
    field_level_confidence,
)


PAYLOAD = b"P3B'/9B"


def main():
    print("Carrier -> PhoxoidField adapter test")
    print("=" * 60)
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        carrier_png = td / 'carrier.png'
        info = encoder.encode(PAYLOAD, 'test.txt', carrier_png)
        print(f"  encoded carrier ({info['png_bytes']} bytes)")

        # Run spike-9B decode
        res = decoder.decode(carrier_png)
        assert res.sha256_ok, f"clean decode should pass: {res.decode_error}"
        print(f"  spike-9B decode: PASS (NCC manifest={res.median_manifest_ncc:.3f})")

        # Re-run the per-germ classifier so we have full
        # (positions, codewords, NCCs) for every site
        params = EncodeParams()
        basis = OrthoBasis.build(params.half_size, params.sigma)
        codebook = design_codebook(basis, n_codewords=params.n_codewords,
                                      seed=params.codebook_seed)
        layout = canonical_layout(CANVAS_WIDTH, CANVAS_HEIGHT)
        captured = np.asarray(Image.open(carrier_png).convert('L'),
                                  dtype=np.float32) / 255.0
        pose = detect_pose(captured, layout)
        rectified = rectify(captured, pose.homography, CANVAS_WIDTH, CANVAS_HEIGHT)
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
        rect_corrected = grid.invert(rectified).astype(np.float32)

        templates = render_codebook_patches(codebook, basis,
                                              params.amp, params.baseline)
        germ_indices = MANIFEST_INDICES + PAYLOAD_INDICES
        germ_positions = [grid_index_to_pixel(i) for i in germ_indices]
        decoded_codewords = []
        nccs = []
        for cx, cy in germ_positions:
            x0 = cx - params.half_size; x1 = cx + params.half_size + 1
            y0 = cy - params.half_size; y1 = cy + params.half_size + 1
            patch = rect_corrected[y0:y1, x0:x1].astype(np.float32)
            best_idx, ncc, _ = classify_patch(patch, templates)
            decoded_codewords.append(best_idx)
            nccs.append(ncc)

        # Wrap as PhoxoidField
        field = carrier_decode_to_phoxoid_field(
            decode_result=res,
            decoded_codewords_per_germ=decoded_codewords,
            germ_positions=germ_positions,
            germ_nccs=nccs,
            params=params,
        )
        print(f"  PhoxoidField: id={field.field_id}, n_sites={field.n_sites}, "
                f"dim={field.dimensionality}, codebook={field.codebook_ref[:8]}...")
        flc = field_level_confidence(field)
        print(f"  field-level confidence: {flc}")

        errs = validate_field(field)
        assert not errs, f"validation errors: {errs}"
        print(f"  validate_field: PASS")

        # JSON round-trip
        out = td / 'field.json'
        write_json(field, out)
        field2 = read_json(out)
        assert field2.n_sites == field.n_sites
        assert field2.field_id == field.field_id
        assert field2.codebook_ref == field.codebook_ref
        for s1, s2 in zip(field.sites, field2.sites):
            assert np.allclose(s1.position, s2.position)
            assert np.allclose(s1.germ.coeffs, s2.germ.coeffs)
        print(f"  JSON round-trip: PASS")

        # Compose with itself (sanity)
        field_b = carrier_decode_to_phoxoid_field(
            decode_result=res,
            decoded_codewords_per_germ=decoded_codewords,
            germ_positions=germ_positions,
            germ_nccs=nccs,
            params=params,
            field_id='phox-second',
        )
        composed = compose_fields(field, field_b)
        print(f"  compose_fields: PASS (n_sites={composed.n_sites}, "
                f"derived_from={composed.audit.derived_from})")
        assert composed.n_sites == 2 * field.n_sites
        flc2 = field_level_confidence(composed)
        print(f"  composed field-level confidence: {flc2} (expect downgrade vs {flc})")

        print(f"\n  out_json (first 400 chars):")
        print(out.read_text()[:400] + " ...")

    print("=" * 60)
    print("ALL TESTS PASS")


if __name__ == '__main__':
    main()
