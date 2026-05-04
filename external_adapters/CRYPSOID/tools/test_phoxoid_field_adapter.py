"""End-to-end test of CRYPSOID's phoxoid_field adapter.

Tests:
  1. Load a real .3dphox file -> SplatBuffer -> PhoxoidField
  2. Validate the field
  3. JSON wire-format round-trip (phoxoid_field-side; lossless)
  4. PhoxoidField -> SplatBuffer round-trip (in-memory; loses
     higher-order germ coefficients per v0.1.0 constraint)

Skips gracefully if no .3dphox file is available.
"""
from __future__ import annotations
import sys
import tempfile
from pathlib import Path

import numpy as np

_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE))

from phoxoid_field import (
    PhoxoidField, write_json, read_json, validate_field, compose_fields,
    field_level_confidence,
)
from phoxoid_field_adapter import (
    splat_buffer_to_phoxoid_field, phox3d_path_to_phoxoid_field,
    phoxoid_field_to_splat_buffer,
)
from crypsorender.io.phox_loader import load_3dphox_v28_render


def find_test_phox3d():
    """Find any v28 .3dphox file we can test against."""
    candidates = [
        _HERE.parent / 'outputs' / 'v28_sh_vq_render_container.3dphox',
        _HERE.parent / 'recovery_v2' / 'v27_attribute_group_sh_vq_render_container.3dphox',
    ]
    for c in candidates:
        if c.exists():
            return c
    # Fall back to globbing
    matches = list((_HERE.parent / 'outputs').glob('*v28*.3dphox'))
    return matches[0] if matches else None


def test_load_and_convert():
    p = find_test_phox3d()
    if p is None:
        print("  test_load_and_convert: SKIPPED (no .3dphox file found)")
        return None
    print(f"  loading: {p.name}")
    buf = load_3dphox_v28_render(p)
    print(f"  loaded SplatBuffer: n={buf.n}, format={buf.scene_format}, "
            f"has_germ={buf.germ is not None}")
    field = splat_buffer_to_phoxoid_field(buf, field_id='test-cryp-001')
    print(f"  PhoxoidField: n_sites={field.n_sites}, dim={field.dimensionality}")
    errs = validate_field(field)
    assert not errs, f"validation errors: {errs}"
    print(f"  validate_field: PASS")
    flc = field_level_confidence(field)
    print(f"  field-level confidence: {flc} "
            f"(expected NEED_MORE_EVIDENCE since CRYPSOID v0.1.x lacks higher-order germ data)")
    return field


def test_json_roundtrip(field):
    if field is None:
        print("  test_json_roundtrip: SKIPPED (no field)")
        return
    # Subsample to keep the test small (full Audi scene = millions of sites)
    if field.n_sites > 100:
        print(f"  subsampling {field.n_sites} -> 100 sites for JSON roundtrip test")
        sub = PhoxoidField(
            field_id=field.field_id + '_sub',
            dimensionality=field.dimensionality,
            sites=field.sites[:100],
            audit=field.audit,
            codebook_ref=field.codebook_ref,
        )
    else:
        sub = field
    with tempfile.TemporaryDirectory() as td:
        out = Path(td) / 'field.json'
        write_json(sub, out)
        sub2 = read_json(out)
        assert sub2.n_sites == sub.n_sites
        for s1, s2 in zip(sub.sites, sub2.sites):
            assert np.allclose(s1.position, s2.position), "position drift"
            assert np.allclose(s1.germ.coeffs, s2.germ.coeffs), "germ drift"
    print("  test_json_roundtrip: PASS")


def test_inverse_to_splat_buffer(field):
    if field is None:
        print("  test_inverse_to_splat_buffer: SKIPPED (no field)")
        return
    if field.n_sites > 100:
        sub = PhoxoidField(
            field_id=field.field_id + '_sub',
            dimensionality=field.dimensionality,
            sites=field.sites[:100],
            audit=field.audit, codebook_ref=field.codebook_ref,
        )
    else:
        sub = field
    buf2 = phoxoid_field_to_splat_buffer(sub)
    print(f"  PhoxoidField -> SplatBuffer: n={buf2.n}, format={buf2.scene_format}, "
            f"has_germ={buf2.germ is not None}")
    assert buf2.n == sub.n_sites
    print("  test_inverse_to_splat_buffer: PASS")


def main():
    print("CRYPSOID phoxoid_field adapter test")
    print("=" * 60)
    field = test_load_and_convert()
    test_json_roundtrip(field)
    test_inverse_to_splat_buffer(field)
    print("=" * 60)
    print("DONE")


if __name__ == '__main__':
    main()
