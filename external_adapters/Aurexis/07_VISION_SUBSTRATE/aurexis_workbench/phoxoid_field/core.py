"""Core dtype classes for phoxoid_field v0.1.0.

Per SPEC_phoxoid_field_v0.1.md §2.
"""
from __future__ import annotations
from dataclasses import dataclass, field as dc_field
from typing import Any
import numpy as np


SPEC_VERSION = "v0.1.0"
BASIS_PEARCEY5 = "pearcey5"   # locked per Q1 resolution


# 5-valued confidence lattice — Aurexis (per spec §2)
class ConfidenceState:
    TRUST = "TRUST"
    HOLD = "HOLD"
    DOWNGRADE = "DOWNGRADE"
    REJECT = "REJECT"
    NEED_MORE_EVIDENCE = "NEED_MORE_EVIDENCE"

    ALL = (TRUST, HOLD, DOWNGRADE, REJECT, NEED_MORE_EVIDENCE)

    @classmethod
    def is_valid(cls, s: str) -> bool:
        return s in cls.ALL


# Worst-of-with-one-step-downgrade ordering. NEED_MORE_EVIDENCE absorbs.
# REJECT absorbs (any composition that hits REJECT stays REJECT).
# Otherwise: composition steps confidence one notch toward DOWNGRADE.
_CONFIDENCE_ORDER = {
    ConfidenceState.TRUST: 0,
    ConfidenceState.HOLD: 1,
    ConfidenceState.DOWNGRADE: 2,
    ConfidenceState.REJECT: 3,
    ConfidenceState.NEED_MORE_EVIDENCE: 4,
}
_CONFIDENCE_DOWNGRADE_STEP = {
    ConfidenceState.TRUST: ConfidenceState.HOLD,
    ConfidenceState.HOLD: ConfidenceState.DOWNGRADE,
    ConfidenceState.DOWNGRADE: ConfidenceState.DOWNGRADE,
    ConfidenceState.REJECT: ConfidenceState.REJECT,
    ConfidenceState.NEED_MORE_EVIDENCE: ConfidenceState.NEED_MORE_EVIDENCE,
}


def compose_confidence(a: str, b: str) -> str:
    """Worst-of-with-one-step-downgrade per spec §4.

    Examples:
      TRUST × TRUST = HOLD          (one downgrade tick per composition)
      TRUST × HOLD = DOWNGRADE
      TRUST × REJECT = REJECT       (REJECT absorbs)
      any × NEED_MORE_EVIDENCE = NEED_MORE_EVIDENCE
    """
    if not (ConfidenceState.is_valid(a) and ConfidenceState.is_valid(b)):
        raise ValueError(f"invalid confidence states: {a!r}, {b!r}")
    if ConfidenceState.NEED_MORE_EVIDENCE in (a, b):
        return ConfidenceState.NEED_MORE_EVIDENCE
    if ConfidenceState.REJECT in (a, b):
        return ConfidenceState.REJECT
    # Worst of the two, then one downgrade step
    worst = a if _CONFIDENCE_ORDER[a] >= _CONFIDENCE_ORDER[b] else b
    return _CONFIDENCE_DOWNGRADE_STEP[worst]


@dataclass
class GermCoefficients:
    """5-coefficient catastrophe-germ in the locked Pearcey basis.

    coeffs order: (κ₁, κ₂, χ, ω, ζ) per CRYPSOID thesis_digest.md §2 Layer 2.
    quality ∈ [0, 1]: fit residual or classifier margin.
    """
    coeffs: np.ndarray   # shape (5,) float32
    quality: float = 1.0
    basis: str = BASIS_PEARCEY5

    def __post_init__(self):
        c = np.asarray(self.coeffs, dtype=np.float32)
        if c.shape != (5,):
            raise ValueError(f"coeffs must be shape (5,), got {c.shape}")
        self.coeffs = c
        if not (0.0 <= self.quality <= 1.0):
            raise ValueError(f"quality must be in [0, 1], got {self.quality}")
        if self.basis != BASIS_PEARCEY5:
            raise ValueError(f"v0.1.0 locks basis to {BASIS_PEARCEY5!r}, got {self.basis!r}")


@dataclass
class PhoxoidSite:
    """One catastrophe-germ site with position, frame, germ, softness, confidence.

    For 2D fields (dimensionality=2):
      position: shape (2,)
      frame: shape (2, 2)  (rotation in canvas plane)
      softness: shape (4,) — σ_n unused, conventionally set to 0
    For 3D fields:
      position: shape (3,)
      frame: shape (3, 3)
      softness: shape (4,) — full (σ_a, σ_b, σ_n, τ)
    """
    site_id: int
    position: np.ndarray
    frame: np.ndarray
    germ: GermCoefficients
    softness: np.ndarray
    confidence: str = ConfidenceState.TRUST
    extra: dict = dc_field(default_factory=dict)

    def __post_init__(self):
        self.position = np.asarray(self.position, dtype=np.float32)
        self.frame = np.asarray(self.frame, dtype=np.float32)
        self.softness = np.asarray(self.softness, dtype=np.float32)
        if not ConfidenceState.is_valid(self.confidence):
            raise ValueError(f"invalid confidence state: {self.confidence!r}")
        if self.position.ndim != 1 or self.position.shape[0] not in (2, 3):
            raise ValueError(f"position must be (2,) or (3,), got shape {self.position.shape}")
        D = self.position.shape[0]
        if self.frame.shape != (D, D):
            raise ValueError(f"frame must be ({D},{D}) for D={D}, got {self.frame.shape}")
        if self.softness.shape != (4,):
            raise ValueError(f"softness must be (4,), got {self.softness.shape}")


@dataclass
class AuditMetadata:
    """Provenance of a PhoxoidField. Append-only.

    derived_from: field_ids of source fields (empty for fresh fields).
    operations: ordered list of operation names applied (e.g.
                ["carrier.decode", "compose_fields"]).
    hash_chain: SHA-256 anchors after each operation (parallel to operations).
    timestamp: ISO 8601 of field creation.
    """
    derived_from: list = dc_field(default_factory=list)
    operations: list = dc_field(default_factory=list)
    hash_chain: list = dc_field(default_factory=list)
    timestamp: str = ""

    def __post_init__(self):
        if len(self.operations) != len(self.hash_chain):
            raise ValueError(
                f"operations and hash_chain must be parallel; got "
                f"{len(self.operations)} ops and {len(self.hash_chain)} hashes"
            )


@dataclass
class PhoxoidField:
    """A collection of catastrophe-germ sites — the canonical substrate dtype.

    Per SPEC_phoxoid_field_v0.1.md §2.
    """
    field_id: str
    dimensionality: int
    sites: list                # list of PhoxoidSite
    audit: AuditMetadata
    codebook_ref: str = ""     # SHA-256 of canonical codebook serialization, or empty
    version: str = SPEC_VERSION

    def __post_init__(self):
        if self.dimensionality not in (2, 3):
            raise ValueError(f"dimensionality must be 2 or 3, got {self.dimensionality}")
        for s in self.sites:
            if not isinstance(s, PhoxoidSite):
                raise TypeError(f"sites must contain PhoxoidSite, got {type(s).__name__}")
            if s.position.shape[0] != self.dimensionality:
                raise ValueError(
                    f"site {s.site_id} dimensionality {s.position.shape[0]} "
                    f"!= field dimensionality {self.dimensionality}"
                )

    @property
    def n_sites(self) -> int:
        return len(self.sites)


def field_level_confidence(field: PhoxoidField) -> str:
    """Derived field-level confidence per Q2 resolution: computed on demand.

    Strategy: take the WORST per-site confidence, then apply one downgrade
    step per composition recorded in the audit (so a field that has been
    composed many times and started TRUST will drift toward DOWNGRADE).
    """
    if not field.sites:
        return ConfidenceState.NEED_MORE_EVIDENCE
    # Worst per-site
    worst_idx = max(_CONFIDENCE_ORDER[s.confidence] for s in field.sites)
    inv = {v: k for k, v in _CONFIDENCE_ORDER.items()}
    worst = inv[worst_idx]
    # Compositional drift: one downgrade tick per recorded composition op
    n_compositions = sum(1 for op in field.audit.operations
                          if 'compose' in op.lower())
    result = worst
    for _ in range(n_compositions):
        result = _CONFIDENCE_DOWNGRADE_STEP[result]
    return result
