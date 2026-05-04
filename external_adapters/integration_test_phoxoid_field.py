"""Cross-tree integration test for phoxoid_field v0.1.0.

Run this AFTER you've installed the adapters into both partner forks
and confirmed each works locally.

What this test does:
  1. Creates a synthetic PhoxoidField directly via the canonical package
  2. JSON-roundtrips it (so the JSON wire format is the cross-tree
     handoff medium)
  3. Composes two fields and verifies the audit trail is intact

This test does NOT require CRYPSOID or Aurexis to be importable from
within crypscan — those adapters are tested inside their own forks.
This test exercises the SHARED-DTYPE invariants that all three trees
must honor, regardless of which tree produced/consumed the field.

Usage:
  cd <crypscan-checkout>
  python3 external_adapters/integration_test_phoxoid_field.py
"""
from __future__ import annotations
import json
import sys
import tempfile
from pathlib import Path

import numpy as np

# Make sure the canonical package is on sys.path
_HERE = Path(__file__).resolve().parent
_REPO = _HERE.parent
sys.path.insert(0, str(_REPO))

from phoxoid_field import (
    PhoxoidField, PhoxoidSite, GermCoefficients, AuditMetadata,
    ConfidenceState, write_json, read_json, validate_field, compose_fields,
    field_level_confidence,
)
from phoxoid_field.audit import new_audit, hash_field


def make_synthetic_3d_field(field_id: str, n_sites: int = 10) -> PhoxoidField:
    """Create a small synthetic 3D PhoxoidField (CRYPSOID-shaped)."""
    rng = np.random.default_rng(seed=42)
    sites = []
    for i in range(n_sites):
        position = rng.uniform(-10, 10, size=3).astype(np.float32)
        frame = np.eye(3, dtype=np.float32)
        coeffs = rng.uniform(-1, 1, size=5).astype(np.float32)
        germ = GermCoefficients(coeffs=coeffs, quality=0.85)
        softness = np.array([1.0, 1.0, 1.0, 1.0], dtype=np.float32)
        sites.append(PhoxoidSite(
            site_id=i, position=position, frame=frame,
            germ=germ, softness=softness,
            confidence=ConfidenceState.HOLD,
            extra={'simulated_origin': 'CRYPSOID', 'tier': 0},
        ))
    field = PhoxoidField(
        field_id=field_id, dimensionality=3,
        sites=sites, audit=AuditMetadata(),
        codebook_ref="",
    )
    field.audit = new_audit('test.crypsoid_synthetic', field)
    return field


def make_synthetic_2d_field(field_id: str, n_sites: int = 10) -> PhoxoidField:
    """Create a small synthetic 2D PhoxoidField (carrier-shaped)."""
    rng = np.random.default_rng(seed=99)
    sites = []
    for i in range(n_sites):
        position = rng.uniform(0, 1280, size=2).astype(np.float32)
        frame = np.eye(2, dtype=np.float32)
        coeffs = rng.uniform(-0.5, 0.5, size=5).astype(np.float32)
        germ = GermCoefficients(coeffs=coeffs, quality=0.92)
        softness = np.array([8.0, 8.0, 0.0, 1.0], dtype=np.float32)
        sites.append(PhoxoidSite(
            site_id=i, position=position, frame=frame,
            germ=germ, softness=softness,
            confidence=ConfidenceState.TRUST,
            extra={'simulated_origin': 'phoxoidal_carrier'},
        ))
    field = PhoxoidField(
        field_id=field_id, dimensionality=2,
        sites=sites, audit=AuditMetadata(),
        codebook_ref="abc123" + "0" * 58,
    )
    field.audit = new_audit('test.carrier_synthetic', field)
    return field


def test_cross_tree_invariants():
    """The shared dtype invariants every tree must honor."""
    cryp = make_synthetic_3d_field('phox-cryp-001', n_sites=10)
    car = make_synthetic_2d_field('phox-car-001', n_sites=10)

    # Both must validate
    assert not validate_field(cryp), f"CRYPSOID-shaped field invalid: {validate_field(cryp)}"
    assert not validate_field(car), f"Carrier-shaped field invalid: {validate_field(car)}"
    print("  cross-tree validation: PASS")

    # Both must JSON round-trip without drift
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        write_json(cryp, td / 'cryp.json')
        cryp2 = read_json(td / 'cryp.json')
        assert hash_field(cryp) == hash_field(cryp2), "CRYPSOID-shaped JSON drift"
        write_json(car, td / 'car.json')
        car2 = read_json(td / 'car.json')
        assert hash_field(car) == hash_field(car2), "Carrier-shaped JSON drift"
    print("  cross-tree JSON round-trip: PASS")

    # Same-dimensionality composition must work
    cryp_b = make_synthetic_3d_field('phox-cryp-002', n_sites=5)
    composed_3d = compose_fields(cryp, cryp_b)
    assert composed_3d.n_sites == 15
    assert composed_3d.audit.derived_from == ['phox-cryp-001', 'phox-cryp-002']
    print(f"  compose 3D × 3D: PASS (n_sites={composed_3d.n_sites})")

    # Mixed-dimensionality composition must reject
    try:
        compose_fields(cryp, car)
        raise AssertionError("compose_fields should reject mixed-dim")
    except ValueError as e:
        assert 'dimensionality' in str(e)
    print("  reject mixed-dim composition: PASS")

    # Field-level confidence reflects per-site + composition history
    flc_cryp = field_level_confidence(cryp)
    flc_car = field_level_confidence(car)
    flc_composed = field_level_confidence(composed_3d)
    print(f"  field-level confidence: CRYPSOID={flc_cryp}  carrier={flc_car}  "
            f"composed={flc_composed}")
    # composed should be one downgrade tick from worst per-site
    assert flc_composed != flc_cryp, (
        f"composition should drift confidence; got {flc_composed} from {flc_cryp}"
    )
    print(f"  composition drifts confidence: PASS")


def test_audit_chain_integrity():
    """Mutating a field's content after creation must be detectable."""
    field = make_synthetic_3d_field('phox-audit-001', n_sites=5)
    original_hash = field.audit.hash_chain[0]
    # Mutate a site's germ
    field.sites[0].germ.coeffs[0] = 999.0
    new_hash = hash_field(field)
    assert new_hash != original_hash, "audit chain failed to detect mutation"
    print(f"  audit-chain mutation detection: PASS")
    print(f"    original: {original_hash[:16]}...")
    print(f"    after mutation: {new_hash[:16]}...")


def main():
    print("Cross-tree integration test: phoxoid_field v0.1.0")
    print("=" * 60)
    test_cross_tree_invariants()
    test_audit_chain_integrity()
    print("=" * 60)
    print("ALL CROSS-TREE INVARIANTS HOLD")
    print()
    print("This test validates that the SHARED DTYPE works correctly.")
    print("To validate that each TREE'S ADAPTER produces conformant fields,")
    print("run the per-tree tests inside each fork:")
    print("  CRYPSOID:  cd CRYPSOID && python3 tools/test_phoxoid_field_adapter.py")
    print("  carrier:   cd crypscan/phoxcar/spike9b && python3 test_phoxoid_field_adapter.py")
    print("  Aurexis:   (test entry point pending Vince's review of the operators)")


if __name__ == '__main__':
    main()
