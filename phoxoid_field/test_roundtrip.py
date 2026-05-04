"""Smoke test: PhoxoidField construct → JSON wire → read → validate → compose.

Runs without any tree-specific dependencies (no CRYPSOID, no Aurexis,
no carrier import). Tests the canonical core library only.
"""
from __future__ import annotations
import sys
import tempfile
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from phoxoid_field import (
    PhoxoidField, PhoxoidSite, GermCoefficients, AuditMetadata,
    ConfidenceState, write_json, read_json, validate_field, compose_fields,
    field_level_confidence, compose_confidence,
)
from phoxoid_field.audit import new_audit, hash_field


def _make_test_field(field_id: str, n_sites: int, dim: int = 2) -> PhoxoidField:
    """Build a small synthetic PhoxoidField for testing."""
    sites = []
    rng = np.random.default_rng(42 + n_sites)
    for i in range(n_sites):
        position = rng.uniform(0, 1280, size=dim).astype(np.float32)
        frame = np.eye(dim, dtype=np.float32)
        coeffs = rng.uniform(-1, 1, size=5).astype(np.float32)
        germ = GermCoefficients(coeffs=coeffs, quality=0.85)
        softness = np.array([4.0, 4.0, 0.0, 1.0], dtype=np.float32)
        sites.append(PhoxoidSite(
            site_id=i, position=position, frame=frame,
            germ=germ, softness=softness, confidence=ConfidenceState.TRUST,
        ))
    field = PhoxoidField(
        field_id=field_id, dimensionality=dim,
        sites=sites, audit=AuditMetadata(),
        codebook_ref="0" * 64,
    )
    field.audit = new_audit('test.create', field)
    return field


def test_validation():
    f = _make_test_field('phox-aaa', 3)
    errors = validate_field(f)
    assert not errors, f"unexpected validation errors: {errors}"
    print("  test_validation: PASS")


def test_jsonwire_roundtrip():
    f = _make_test_field('phox-bbb', 5)
    with tempfile.TemporaryDirectory() as td:
        out = Path(td) / 'field.json'
        write_json(f, out)
        f2 = read_json(out)
    # Verify content equality
    assert f.field_id == f2.field_id
    assert f.dimensionality == f2.dimensionality
    assert len(f.sites) == len(f2.sites)
    for s1, s2 in zip(f.sites, f2.sites):
        assert np.allclose(s1.position, s2.position)
        assert np.allclose(s1.frame, s2.frame)
        assert np.allclose(s1.germ.coeffs, s2.germ.coeffs)
        assert s1.confidence == s2.confidence
    # Verify hash chain match
    assert hash_field(f) == hash_field(f2), "hash drift across JSON round-trip"
    print("  test_jsonwire_roundtrip: PASS")


def test_compose_fields():
    a = _make_test_field('phox-aaa', 3)
    b = _make_test_field('phox-bbb', 4)
    c = compose_fields(a, b)
    assert c.n_sites == 7
    assert c.audit.derived_from == ['phox-aaa', 'phox-bbb']
    assert c.audit.operations == ['compose_fields']
    assert len(c.audit.hash_chain) == 1
    # Field-level confidence: TRUST sites + 1 composition = HOLD
    flc = field_level_confidence(c)
    assert flc == ConfidenceState.HOLD, f"expected HOLD, got {flc}"
    print(f"  test_compose_fields: PASS (composed n_sites={c.n_sites}, field_conf={flc})")


def test_confidence_arithmetic():
    # Per spec §4
    assert compose_confidence(ConfidenceState.TRUST, ConfidenceState.TRUST) == ConfidenceState.HOLD
    assert compose_confidence(ConfidenceState.TRUST, ConfidenceState.HOLD) == ConfidenceState.DOWNGRADE
    assert compose_confidence(ConfidenceState.TRUST, ConfidenceState.REJECT) == ConfidenceState.REJECT
    assert compose_confidence(ConfidenceState.TRUST, ConfidenceState.NEED_MORE_EVIDENCE) == ConfidenceState.NEED_MORE_EVIDENCE
    print("  test_confidence_arithmetic: PASS")


def test_dimensionality_mismatch_rejected():
    a = _make_test_field('phox-2d', 3, dim=2)
    b = _make_test_field('phox-3d', 3, dim=3)
    try:
        compose_fields(a, b)
        raise AssertionError("compose_fields should have rejected mixed-dim fields")
    except ValueError as e:
        assert 'dimensionality' in str(e), f"unexpected error: {e}"
    print("  test_dimensionality_mismatch_rejected: PASS")


def main():
    print("phoxoid_field v0.1.0 core library smoke tests")
    print("=" * 60)
    test_validation()
    test_jsonwire_roundtrip()
    test_compose_fields()
    test_confidence_arithmetic()
    test_dimensionality_mismatch_rejected()
    print("=" * 60)
    print("ALL TESTS PASS")


if __name__ == '__main__':
    main()
