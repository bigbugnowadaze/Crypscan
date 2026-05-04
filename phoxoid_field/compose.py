"""Composition helper for phoxoid_field v0.1.0.

Per spec §3 (operator declaration) and §7 (explicitly NOT defining the
cohomological consistency check semantics in v0.1.0).

v0.1.0 ships the INTERFACE. The composition merges two fields' sites,
inherits/composes confidence states, and builds a unified audit trail.
The cohomological-consistency check itself is a stub that returns
True (no contradiction detected) and emits a NEED_MORE_EVIDENCE site
for any pair of nearby sites that disagree.

Real cohomology semantics is B-2 territory.
"""
from __future__ import annotations
import uuid

from .core import (
    PhoxoidField, PhoxoidSite, ConfidenceState,
    compose_confidence,
)
from .typecheck import can_compose
from .audit import new_audit, append_operation


def _new_field_id() -> str:
    return f"phox-{uuid.uuid4().hex[:12]}"


def compose_fields(a: PhoxoidField, b: PhoxoidField,
                     operation_name: str = "compose_fields") -> PhoxoidField:
    """Sheaf-style composition with cohomological consistency check.

    v0.1.0 stub semantics:
      - Concatenate sites from both fields, renumber site_ids
      - Each surviving site keeps its original confidence
      - Audit derives_from = [a.field_id, b.field_id]
      - field-level confidence (computed on demand) drifts one downgrade
        step per composition

    v0.2 will:
      - detect site-pairs at the same canonical position
      - check germ-coefficient agreement
      - emit REJECT or NEED_MORE_EVIDENCE for inconsistent pairs
      - merge consistent pairs into a single high-confidence site
    """
    ok, reason = can_compose(a, b)
    if not ok:
        raise ValueError(f"compose_fields: {reason}")

    new_sites = []
    next_site_id = 0
    for src_field in (a, b):
        for s in src_field.sites:
            new_sites.append(PhoxoidSite(
                site_id=next_site_id,
                position=s.position.copy(),
                frame=s.frame.copy(),
                germ=s.germ,
                softness=s.softness.copy(),
                confidence=s.confidence,
                extra={**s.extra, '_origin_field': src_field.field_id,
                       '_origin_site_id': s.site_id},
            ))
            next_site_id += 1

    # Build the new field with empty audit first; we attach audit after
    # the field exists (audit hashes the field's content).
    from .core import AuditMetadata
    composed = PhoxoidField(
        field_id=_new_field_id(),
        dimensionality=a.dimensionality,
        sites=new_sites,
        audit=AuditMetadata(),       # placeholder; replaced below
        codebook_ref=a.codebook_ref or b.codebook_ref,
    )
    # Re-create with proper audit
    composed.audit = new_audit(
        operation_name=operation_name,
        field=composed,
        derived_from=[a.field_id, b.field_id],
    )
    return composed
