"""JSON wire format for phoxoid_field v0.1.0.

Per spec §2: JSON for everything except `coeffs` and `frame`, which are
inlined as base64-encoded little-endian float32 blobs to avoid float-print
drift.
"""
from __future__ import annotations
import base64
import json
from pathlib import Path
import numpy as np

from .core import (
    PhoxoidField, PhoxoidSite, GermCoefficients, AuditMetadata,
    ConfidenceState, SPEC_VERSION,
)


def _np_to_b64(arr: np.ndarray) -> str:
    return base64.b64encode(arr.astype(np.float32).tobytes()).decode('ascii')


def _b64_to_np(s: str, shape: tuple) -> np.ndarray:
    raw = base64.b64decode(s.encode('ascii'))
    return np.frombuffer(raw, dtype=np.float32).reshape(shape).copy()


def field_to_dict(field: PhoxoidField) -> dict:
    """Serialize a PhoxoidField to a JSON-safe dict."""
    sites_out = []
    for s in field.sites:
        sites_out.append({
            'site_id': int(s.site_id),
            'position_b64': _np_to_b64(s.position),
            'frame_b64': _np_to_b64(s.frame),
            'frame_shape': list(s.frame.shape),
            'germ': {
                'coeffs_b64': _np_to_b64(s.germ.coeffs),
                'quality': float(s.germ.quality),
                'basis': s.germ.basis,
            },
            'softness_b64': _np_to_b64(s.softness),
            'confidence': s.confidence,
            'extra': s.extra,
        })
    return {
        'spec_version': SPEC_VERSION,
        'field_id': field.field_id,
        'dimensionality': int(field.dimensionality),
        'codebook_ref': field.codebook_ref,
        'sites': sites_out,
        'audit': {
            'derived_from': list(field.audit.derived_from),
            'operations': list(field.audit.operations),
            'hash_chain': list(field.audit.hash_chain),
            'timestamp': field.audit.timestamp,
        },
    }


def field_from_dict(d: dict) -> PhoxoidField:
    """Deserialize a PhoxoidField from a JSON-safe dict."""
    if d.get('spec_version', '') != SPEC_VERSION:
        raise ValueError(
            f"unsupported spec_version {d.get('spec_version')!r} (expected {SPEC_VERSION!r})"
        )
    D = int(d['dimensionality'])
    sites = []
    for s in d['sites']:
        position = _b64_to_np(s['position_b64'], (D,))
        frame = _b64_to_np(s['frame_b64'], tuple(s['frame_shape']))
        germ_coeffs = _b64_to_np(s['germ']['coeffs_b64'], (5,))
        germ = GermCoefficients(
            coeffs=germ_coeffs,
            quality=float(s['germ']['quality']),
            basis=s['germ']['basis'],
        )
        softness = _b64_to_np(s['softness_b64'], (4,))
        sites.append(PhoxoidSite(
            site_id=int(s['site_id']),
            position=position,
            frame=frame,
            germ=germ,
            softness=softness,
            confidence=s['confidence'],
            extra=dict(s.get('extra') or {}),
        ))
    audit = AuditMetadata(
        derived_from=list(d['audit'].get('derived_from') or []),
        operations=list(d['audit'].get('operations') or []),
        hash_chain=list(d['audit'].get('hash_chain') or []),
        timestamp=str(d['audit'].get('timestamp') or ''),
    )
    return PhoxoidField(
        field_id=d['field_id'],
        dimensionality=D,
        sites=sites,
        audit=audit,
        codebook_ref=str(d.get('codebook_ref') or ''),
        version=d['spec_version'],
    )


def write_json(field: PhoxoidField, path: Path | str) -> Path:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(field_to_dict(field), indent=2))
    return p


def read_json(path: Path | str) -> PhoxoidField:
    p = Path(path)
    return field_from_dict(json.loads(p.read_text()))
