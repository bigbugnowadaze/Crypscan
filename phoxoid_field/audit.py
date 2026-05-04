"""Audit-chain construction for phoxoid_field v0.1.0.

Per SPEC §5: every operation that produces a new field appends to
`audit.operations` and emits a new SHA-256 anchor.
"""
from __future__ import annotations
import hashlib
import json
from datetime import datetime, timezone
import numpy as np

from .core import PhoxoidField, AuditMetadata


def _site_payload_for_hashing(site) -> dict:
    """Canonical-bytes representation of a site for hashing. Stable
    across runs; floats serialized via .tobytes() for byte-exact reproducibility."""
    return {
        'site_id': int(site.site_id),
        'position_b': site.position.astype(np.float32).tobytes().hex(),
        'frame_b': site.frame.astype(np.float32).tobytes().hex(),
        'germ_coeffs_b': site.germ.coeffs.astype(np.float32).tobytes().hex(),
        'germ_quality': float(site.germ.quality),
        'germ_basis': site.germ.basis,
        'softness_b': site.softness.astype(np.float32).tobytes().hex(),
        'confidence': site.confidence,
        'extra': site.extra,
    }


def hash_field(field: PhoxoidField) -> str:
    """SHA-256 hex digest of the field's content (excluding audit metadata).

    The audit hash chain is built FROM these content hashes, so the chain
    itself isn't included in what's hashed.
    """
    h = hashlib.sha256()
    h.update(field.version.encode('utf-8'))
    h.update(b'|')
    h.update(field.field_id.encode('utf-8'))
    h.update(b'|')
    h.update(str(field.dimensionality).encode('utf-8'))
    h.update(b'|')
    h.update(field.codebook_ref.encode('utf-8'))
    h.update(b'|')
    for s in field.sites:
        site_repr = _site_payload_for_hashing(s)
        h.update(json.dumps(site_repr, sort_keys=True).encode('utf-8'))
        h.update(b'|')
    return h.hexdigest()


def new_audit(operation_name: str, field: PhoxoidField,
                derived_from: list | None = None) -> AuditMetadata:
    """Build a fresh AuditMetadata for a newly-created field."""
    timestamp = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
    initial_hash = hash_field(field)
    return AuditMetadata(
        derived_from=list(derived_from or []),
        operations=[operation_name],
        hash_chain=[initial_hash],
        timestamp=timestamp,
    )


def append_operation(field: PhoxoidField, operation_name: str) -> None:
    """Append an operation to the field's audit and emit a new hash anchor.

    Mutates field.audit in place.
    """
    field.audit.operations.append(operation_name)
    field.audit.hash_chain.append(hash_field(field))
