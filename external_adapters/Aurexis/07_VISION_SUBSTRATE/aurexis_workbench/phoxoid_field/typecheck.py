"""Type-checking helpers for phoxoid_field v0.1.0.

Per spec §4.
"""
from __future__ import annotations
from .core import PhoxoidField, BASIS_PEARCEY5


def validate_field(field: PhoxoidField) -> list:
    """Return a list of validation errors (empty list = field is valid)."""
    errors = []
    if field.dimensionality not in (2, 3):
        errors.append(f"invalid dimensionality {field.dimensionality}")
    for s in field.sites:
        if s.position.shape[0] != field.dimensionality:
            errors.append(
                f"site {s.site_id} position shape {s.position.shape} "
                f"!= field dim {field.dimensionality}"
            )
        if s.germ.basis != BASIS_PEARCEY5:
            errors.append(
                f"site {s.site_id} basis {s.germ.basis!r} != locked {BASIS_PEARCEY5!r}"
            )
    if len(field.audit.operations) != len(field.audit.hash_chain):
        errors.append(
            f"audit operations ({len(field.audit.operations)}) and "
            f"hash_chain ({len(field.audit.hash_chain)}) length mismatch"
        )
    return errors


def can_compose(a: PhoxoidField, b: PhoxoidField) -> tuple[bool, str]:
    """Per spec §4: composition allowed only if dimensionalities match and
    codebook_refs match (or one is empty).

    Returns: (allowed, reason).
    """
    if a.dimensionality != b.dimensionality:
        return False, (
            f"dimensionality mismatch {a.dimensionality} vs {b.dimensionality}; "
            f"explicit projection required (deferred to v0.2)"
        )
    if a.codebook_ref and b.codebook_ref and a.codebook_ref != b.codebook_ref:
        return False, (
            f"codebook_ref mismatch: {a.codebook_ref[:8]}... vs {b.codebook_ref[:8]}..."
        )
    return True, "ok"
