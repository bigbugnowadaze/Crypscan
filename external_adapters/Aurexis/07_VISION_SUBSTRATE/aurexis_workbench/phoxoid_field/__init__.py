"""phoxoid_field — the canonical dtype shared across CRYPSOID + Aurexis + carrier.

Implements `SPEC_phoxoid_field_v0.1.md` (approved v0.1.0).

Closes audit gap G1 from AUDIT_B1_cross_tree_integration.md: this is the
keystone shared-type-system that lets the three trees stop being parallel
slices and become subsystems of one substrate.

This package ships:
  - the dtype classes (PhoxoidField, PhoxoidSite, GermCoefficients,
    AuditMetadata, ConfidenceState)
  - JSON wire format (read/write) per spec §2
  - composition helper with worst-of-with-downgrade confidence arithmetic
  - hash-chain audit construction
  - type-checking helpers

What it deliberately does NOT ship (v0.1.0 scope):
  - the cohomology semantics for compose_fields (interface only)
  - 3D ↔ 2D projection (deferred to v0.2)
  - binary wire format
  - streaming / large-field support
  - the four Aurexis-side predicate operators (those live in the
    Aurexis Workbench)
  - the per-tree adapters (those live with their respective trees)
"""
from __future__ import annotations

from .core import (                                                  # noqa: F401
    PhoxoidField, PhoxoidSite, GermCoefficients, AuditMetadata,
    ConfidenceState, BASIS_PEARCEY5, SPEC_VERSION,
    field_level_confidence, compose_confidence,
)
from .wire import (                                                   # noqa: F401
    write_json, read_json,
)
from .compose import (                                                # noqa: F401
    compose_fields,
)
from .audit import (                                                  # noqa: F401
    new_audit, append_operation, hash_field,
)
from .typecheck import (                                              # noqa: F401
    validate_field, can_compose,
)

__all__ = [
    'PhoxoidField', 'PhoxoidSite', 'GermCoefficients', 'AuditMetadata',
    'ConfidenceState', 'BASIS_PEARCEY5', 'SPEC_VERSION',
    'field_level_confidence', 'compose_confidence',
    'write_json', 'read_json',
    'compose_fields',
    'new_audit', 'append_operation', 'hash_field',
    'validate_field', 'can_compose',
]
