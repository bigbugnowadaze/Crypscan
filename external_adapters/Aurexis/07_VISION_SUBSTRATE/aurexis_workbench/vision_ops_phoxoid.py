"""Phoxoid_field vision operators - extends the Workbench operator
registry with the primitives needed to express predicates over
PhoxoidField fields.

Implements the Aurexis half of SPEC_phoxoid_field_v0.1.0 from
bigbugnowadaze/crypscan. Closes audit gap G2 (the predicate-fiber
side of the substrate integration).

# Dtype

PhoxoidField is a NEW Workbench dtype "phoxoid_field" that must be
added to fields.py VALID_DTYPES. See accompanying patch
phoxoid_field_dtype.patch — apply it to fields.py before importing
this module, OR use the runtime registration helper in
register_phoxoid_dtype() below.

# Operators registered

  dominant_germ_type        : phoxoid_field -> label
                                ("fold" | "cusp" | "swallowtail" | "umbilic" | "flat" | "mixed")
  germ_signature_match      : (phoxoid_field, vector, scalar) -> bool
                                (target_coeffs as length-5 vector, tolerance scalar)
  field_curvature_axis      : phoxoid_field -> label
                                ("x" | "y" | "z" | "none")
  compose_fields            : (phoxoid_field, phoxoid_field) -> phoxoid_field
                                (sheaf-style; v0.1.0 stub semantics — see
                                 phoxoid_field/compose.py)

# Vendored dependency

This module imports from `phoxoid_field/` (vendored copy of
bigbugnowadaze/crypscan@SPEC_phoxoid_field_v0.1).
"""
from __future__ import annotations
import numpy as np

from . import operators as ops
from . import fields as fields_module
from .phoxoid_field import (
    PhoxoidField,
    BASIS_PEARCEY5,
    compose_fields as _compose_fields_impl,
)


# ============================================================
# Dtype registration helper
# ============================================================

def register_phoxoid_dtype() -> None:
    """Add 'phoxoid_field' to the Workbench VALID_DTYPES set.

    Idempotent: safe to call repeatedly.

    NOTE for Vince: ideal long-term is to add 'phoxoid_field' directly to
    fields.VALID_DTYPES at module-load time (in fields.py). This runtime
    registration is the bridge so adapters work without an immediate
    fields.py edit.
    """
    fields_module.VALID_DTYPES.add("phoxoid_field")


# ============================================================
# Catastrophe-germ classification (the catastrophe-theory call)
# ============================================================
#
# The 5-coefficient Pearcey basis: (kappa1, kappa2, chi, omega, zeta)
#
#   Flat              -> all coefficients near zero
#   Curved (kappa)    -> kappa1, kappa2 dominate; chi/omega/zeta small
#   Fold (A2)         -> dominated by kappa1 OR kappa2 (one direction)
#   Cusp (A3)         -> chi or omega dominates (cubic terms)
#   Swallowtail (A4)  -> zeta dominates (quartic term)
#   Umbilic (D-type)  -> mixed cubic + quartic contributions
#
# Per CRYPSOID thesis_digest.md Layer 2 §2.

_FLAT_THRESHOLD = 0.05
_DOMINANCE_THRESHOLD = 0.6   # one term must own at least 60% of the L1 mass to be "dominant"


def _classify_germ(coeffs: np.ndarray) -> str:
    """Classify a single 5-vector germ into a catastrophe type."""
    abs_c = np.abs(coeffs.astype(np.float64))
    total = float(abs_c.sum())
    if total < _FLAT_THRESHOLD:
        return "flat"
    fractions = abs_c / total
    # kappa1, kappa2 dominate (curvature) -> fold
    quad_mass = float(fractions[0] + fractions[1])
    cubic_mass = float(fractions[2] + fractions[3])
    quartic_mass = float(fractions[4])
    if quad_mass > _DOMINANCE_THRESHOLD:
        return "fold"
    if cubic_mass > _DOMINANCE_THRESHOLD:
        return "cusp"
    if quartic_mass > _DOMINANCE_THRESHOLD:
        return "swallowtail"
    if cubic_mass > 0.2 and quartic_mass > 0.2:
        return "umbilic"
    return "mixed"


# ============================================================
# Operator implementations
# ============================================================

def _dominant_germ_type(field: PhoxoidField) -> str:
    """Return the most common catastrophe type across the field's sites."""
    if not field.sites:
        return "flat"
    counts = {}
    for s in field.sites:
        cls = _classify_germ(s.germ.coeffs)
        counts[cls] = counts.get(cls, 0) + 1
    return max(counts, key=counts.get)


def _germ_signature_match(field: PhoxoidField,
                            target_coeffs: np.ndarray,
                            tolerance: float) -> bool:
    """True if the field's median germ matches `target_coeffs` within
    `tolerance` (L2 distance in 5-vector space)."""
    if not field.sites:
        return False
    target = np.asarray(target_coeffs, dtype=np.float64)
    if target.shape != (5,):
        raise ValueError(f"target_coeffs must be length-5, got shape {target.shape}")
    coeffs_stack = np.array([s.germ.coeffs for s in field.sites], dtype=np.float64)
    median_coeffs = np.median(coeffs_stack, axis=0)
    distance = float(np.linalg.norm(median_coeffs - target))
    return distance <= float(tolerance)


def _field_curvature_axis(field: PhoxoidField) -> str:
    """Estimate the dominant curvature axis from the field's site distribution.

    For 2D fields: looks at the spatial distribution of kappa_1 vs kappa_2
    residuals and reports whichever axis (x or y) shows stronger systematic
    variation across position.

    For 3D fields: same idea extended to (x, y, z).

    Returns "none" if no axis dominates.
    """
    if not field.sites:
        return "none"
    if field.dimensionality == 2:
        positions = np.array([s.position for s in field.sites], dtype=np.float64)
        coeffs = np.array([s.germ.coeffs for s in field.sites], dtype=np.float64)
        if positions.shape[0] < 4:
            return "none"
        # Centered positions
        cx = positions[:, 0] - positions[:, 0].mean()
        cy = positions[:, 1] - positions[:, 1].mean()
        # Fit kappa1 ~ ax * cx ; kappa2 ~ ay * cy (proxy: check correlation)
        corr_kappa1_x = abs(np.corrcoef(coeffs[:, 0], cx)[0, 1]) if cx.std() > 1e-6 else 0
        corr_kappa2_y = abs(np.corrcoef(coeffs[:, 1], cy)[0, 1]) if cy.std() > 1e-6 else 0
        if corr_kappa1_x > corr_kappa2_y * 1.2 and corr_kappa1_x > 0.3:
            return "x"
        if corr_kappa2_y > corr_kappa1_x * 1.2 and corr_kappa2_y > 0.3:
            return "y"
        return "none"
    else:
        # 3D — extend the same idea, look at correlation with z too
        positions = np.array([s.position for s in field.sites], dtype=np.float64)
        coeffs = np.array([s.germ.coeffs for s in field.sites], dtype=np.float64)
        if positions.shape[0] < 4:
            return "none"
        centered = positions - positions.mean(axis=0)
        corrs = []
        for axis_idx in range(3):
            for coef_idx in range(2):  # kappa1, kappa2
                if centered[:, axis_idx].std() > 1e-6:
                    c = abs(np.corrcoef(coeffs[:, coef_idx], centered[:, axis_idx])[0, 1])
                    corrs.append((c, axis_idx))
        if not corrs:
            return "none"
        corrs.sort(reverse=True)
        if corrs[0][0] < 0.3:
            return "none"
        if len(corrs) >= 2 and corrs[0][0] < corrs[1][0] * 1.2:
            return "none"  # no clear winner
        return ["x", "y", "z"][corrs[0][1]]


def _compose_fields(a: PhoxoidField, b: PhoxoidField) -> PhoxoidField:
    """Wraps phoxoid_field.compose.compose_fields with operator-friendly
    naming for the operation entry in the audit chain."""
    return _compose_fields_impl(a, b, operation_name="aurexis.compose_fields")


# ============================================================
# Bundle-side adapters (FieldBundle <-> PhoxoidField)
# ============================================================

def field_bundle_to_phoxoid_field(bundle, extractor_op_name: str = "germ_extract_default"):
    """Derive a PhoxoidField from an Aurexis FieldBundle by running a
    germ-extractor operator over its image content.

    NOTE for Vince: v0.1.0 ships this as a STUB. The germ-extractor
    operator (whatever shape it should take — likely something like
    "extract_germs_at_grid(image, spacing) -> phoxoid_field") needs to be
    designed in coordination with CRYPSOID's img2phox compiler. For
    v0.1.0 the bundle adapter is a placeholder that produces an empty
    PhoxoidField with a clear audit note.
    """
    import uuid
    from .phoxoid_field import PhoxoidField, AuditMetadata
    from .phoxoid_field.audit import new_audit
    field = PhoxoidField(
        field_id=f"phox-bundle-{uuid.uuid4().hex[:12]}",
        dimensionality=2,
        sites=[],
        audit=AuditMetadata(),
        codebook_ref="",
    )
    field.audit = new_audit(
        operation_name=f"aurexis.field_bundle_to_phoxoid_field[{extractor_op_name}:STUB]",
        field=field,
    )
    return field


def phoxoid_field_to_field_bundle(field: PhoxoidField):
    """Project a PhoxoidField back into a FieldBundle for predicate
    consumption.

    NOTE for Vince: v0.1.0 ships this as a STUB. Specifically what shape
    of FieldBundle predicates expect (an image rendering of the field?
    a regions list of site bounding boxes? a vector of aggregate
    statistics?) needs partnership input. For v0.1.0, the bundle adapter
    creates an empty FieldBundle with a metadata note pointing at the
    source field.
    """
    from .fields import FieldBundle
    bundle = FieldBundle(name=f"phoxoid_field_view[{field.field_id}]")
    return bundle


# ============================================================
# Registration
# ============================================================

def register_phoxoid_ops() -> None:
    """Register all phoxoid_field operators into the Workbench registry.

    Safe to call multiple times; re-registration is a no-op overwrite.

    Should be called from vision_ops.register_all() at module-load
    time once Vince is comfortable, OR called separately by the
    phoxoid-aware CLI entry point.
    """
    register_phoxoid_dtype()
    R = ops.register
    R("dominant_germ_type", ("phoxoid_field",), "label",
       _dominant_germ_type,
       "Most common catastrophe type across the field's sites "
       "(fold/cusp/swallowtail/umbilic/flat/mixed).")
    R("germ_signature_match", ("phoxoid_field", "vector", "scalar"), "bool",
       _germ_signature_match,
       "True if the field's median germ matches a target 5-vector within tolerance.")
    R("field_curvature_axis", ("phoxoid_field",), "label",
       _field_curvature_axis,
       "Dominant curvature axis from spatial coefficient distribution "
       "(x/y/z/none).")
    R("compose_fields", ("phoxoid_field", "phoxoid_field"), "phoxoid_field",
       _compose_fields,
       "Sheaf-style composition of two PhoxoidFields with audit chaining "
       "(v0.1.0 stub semantics; cohomology check in v0.2).")
