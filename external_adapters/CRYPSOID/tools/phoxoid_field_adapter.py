"""CRYPSOID-side adapter for the canonical phoxoid_field dtype.

Implements the CRYPSOID half of SPEC_phoxoid_field_v0.1.0 (the spec lives
at https://github.com/bigbugnowadaze/crypscan; this is the CRYPSOID-side
implementation that closes audit gap G1 from the same repo).

# What this provides

  splat_buffer_to_phoxoid_field(buf)  -> PhoxoidField
  phox3d_path_to_phoxoid_field(path)  -> PhoxoidField   (convenience: load + convert)
  phoxoid_field_to_splat_buffer(field) -> SplatBuffer   (reverse for round-trip)
  phoxoid_field_to_phox3d_path(...)                     (DEFERRED to v0.2 — see below)

# Mapping from SplatBuffer to PhoxoidField (v0.1.0)

  SplatBuffer field    -> PhoxoidField field
  ------------------------------------------------
  xyz                  -> PhoxoidSite.position  (3D)
  quats (wxyz)         -> PhoxoidSite.frame  (3x3 rotation, derived from quat)
  germ.k1, germ.k2     -> PhoxoidSite.germ.coeffs[0], coeffs[1]
                          (kappa_1, kappa_2 in pearcey5 basis)
  (no source for chi/omega/zeta yet) -> coeffs[2:5] = 0.0
                          confidence downgraded to NEED_MORE_EVIDENCE
                          if germ buffer is missing higher-order terms
  scales               -> PhoxoidSite.softness[:3]  (sigma_a, sigma_b, sigma_n
                          in log space per 3DGS convention; consumer must
                          exp() if linear sigmas needed)
  (tau placeholder)    -> softness[3] = 1.0
  tier                 -> PhoxoidSite.extra['tier']  (0=A, 1=B, 2=C)
  opacities            -> extra['opacity']
  sh_dc                -> extra['sh_dc']  (length-3 list, RGB DC)

# Why phoxoid_field_to_phox3d_path is deferred

The .3dphox writers in CRYPSOID v0.1.x do NOT yet emit native germ chunks
(germ_5coef_f16 / germ_index_u32) — these are spec'd in
docs/v40_native_germ_chunks_spec.md but not implemented. Round-tripping a
PhoxoidField containing nonzero chi/omega/zeta into a .3dphox file would
silently drop those coefficients.

For v0.1.0 of the integration spec, the reverse direction is therefore
limited to the SplatBuffer in-memory representation (phoxoid_field ->
SplatBuffer is implemented). Writing the SplatBuffer back to a .3dphox
file uses CRYPSOID's existing writers, which only round-trip the
fields that v25/v27/v28 containers carry (no higher-order germ data).

To round-trip a full PhoxoidField losslessly through .3dphox, CRYPSOID
needs to land the v40 writer (an open work item per
docs/ROADMAP.md "v0.4+ work queue").

# Vendored dependency

This adapter imports the canonical phoxoid_field package from
tools/phoxoid_field/ — vendored copy of bigbugnowadaze/crypscan's
phoxoid_field/. Re-vendor when the upstream package changes;
VENDOR_INFO.py records the source revision.
"""
from __future__ import annotations
import sys
import uuid
from pathlib import Path
from typing import Optional

import numpy as np

# Make the vendored package importable
_HERE = Path(__file__).resolve().parent
_TOOLS = _HERE
if str(_TOOLS) not in sys.path:
    sys.path.insert(0, str(_TOOLS))

from phoxoid_field import (
    PhoxoidField, PhoxoidSite, GermCoefficients, AuditMetadata,
    ConfidenceState, write_json, read_json, validate_field,
)
from phoxoid_field.audit import new_audit

# Local CRYPSOID imports
from crypsorender.io.splat_buffer import SplatBuffer, GermBuffer
from crypsorender.io.phox_loader import (
    load_3dphox_v28_render,
    # other v25/v27 loaders if needed
)


# ---------- Helpers ----------

def _quat_to_rotation_matrix(quat_wxyz: np.ndarray) -> np.ndarray:
    """Convert a (w, x, y, z) quaternion to a 3x3 rotation matrix."""
    w, x, y, z = float(quat_wxyz[0]), float(quat_wxyz[1]), float(quat_wxyz[2]), float(quat_wxyz[3])
    n = np.sqrt(w*w + x*x + y*y + z*z)
    if n < 1e-9:
        return np.eye(3, dtype=np.float32)
    w, x, y, z = w/n, x/n, y/n, z/n
    return np.array([
        [1 - 2*(y*y + z*z), 2*(x*y - w*z),     2*(x*z + w*y)],
        [2*(x*y + w*z),     1 - 2*(x*x + z*z), 2*(y*z - w*x)],
        [2*(x*z - w*y),     2*(y*z + w*x),     1 - 2*(x*x + y*y)],
    ], dtype=np.float32)


def _rotation_matrix_to_quat(R: np.ndarray) -> np.ndarray:
    """Convert a 3x3 rotation matrix to a (w, x, y, z) quaternion. Standard
    Shepperd's method."""
    R = R.astype(np.float64)
    tr = R[0, 0] + R[1, 1] + R[2, 2]
    if tr > 0:
        s = np.sqrt(tr + 1.0) * 2
        w = 0.25 * s
        x = (R[2, 1] - R[1, 2]) / s
        y = (R[0, 2] - R[2, 0]) / s
        z = (R[1, 0] - R[0, 1]) / s
    elif R[0, 0] > R[1, 1] and R[0, 0] > R[2, 2]:
        s = np.sqrt(1.0 + R[0, 0] - R[1, 1] - R[2, 2]) * 2
        w = (R[2, 1] - R[1, 2]) / s
        x = 0.25 * s
        y = (R[0, 1] + R[1, 0]) / s
        z = (R[0, 2] + R[2, 0]) / s
    elif R[1, 1] > R[2, 2]:
        s = np.sqrt(1.0 + R[1, 1] - R[0, 0] - R[2, 2]) * 2
        w = (R[0, 2] - R[2, 0]) / s
        x = (R[0, 1] + R[1, 0]) / s
        y = 0.25 * s
        z = (R[1, 2] + R[2, 1]) / s
    else:
        s = np.sqrt(1.0 + R[2, 2] - R[0, 0] - R[1, 1]) * 2
        w = (R[1, 0] - R[0, 1]) / s
        x = (R[0, 2] + R[2, 0]) / s
        y = (R[1, 2] + R[2, 1]) / s
        z = 0.25 * s
    return np.array([w, x, y, z], dtype=np.float32)


def _new_field_id(prefix: str = "phox") -> str:
    return f"{prefix}-{uuid.uuid4().hex[:12]}"


# ---------- Forward direction: SplatBuffer -> PhoxoidField ----------

def splat_buffer_to_phoxoid_field(
    buf: SplatBuffer,
    field_id: Optional[str] = None,
) -> PhoxoidField:
    """Convert a CRYPSOID SplatBuffer to the canonical PhoxoidField.

    Each splat becomes one PhoxoidSite. The pearcey5 germ basis carries
    (k1, k2, chi=0, omega=0, zeta=0) — CRYPSOID v0.1.x SplatBuffer.germ
    only stores k1 and k2; higher-order terms are reserved for v0.2+.
    Confidence per-site is set accordingly.
    """
    n = buf.n
    has_germ = buf.germ is not None
    sites = []
    for i in range(n):
        position = buf.xyz[i].astype(np.float32)
        frame = _quat_to_rotation_matrix(buf.quats[i])
        if has_germ:
            k1 = float(buf.germ.k1[i])
            k2 = float(buf.germ.k2[i])
            coeffs = np.array([k1, k2, 0.0, 0.0, 0.0], dtype=np.float32)
            # v0.1.x CRYPSOID stores only k1/k2; the "missing" higher-order
            # coefficients are unknown, not zero. Mark confidence as
            # NEED_MORE_EVIDENCE so consumers don't treat zeros as TRUSTed.
            confidence = ConfidenceState.NEED_MORE_EVIDENCE
            quality = 0.5  # halfway: real lower-order data, missing higher-order
        else:
            # No germ buffer at all -> Tier C / Gaussian fallback per CRYPSOID
            coeffs = np.zeros(5, dtype=np.float32)
            confidence = ConfidenceState.NEED_MORE_EVIDENCE
            quality = 0.0
        germ = GermCoefficients(coeffs=coeffs, quality=quality)
        # softness from log-space scales + tau placeholder
        scales = buf.scales[i].astype(np.float32)
        softness = np.array(
            [scales[0], scales[1], scales[2] if scales.shape[0] > 2 else 0.0, 1.0],
            dtype=np.float32,
        )
        extra = {
            'opacity': float(buf.opacities[i]),
            'sh_dc': buf.sh_dc[i].tolist(),
        }
        if buf.tier is not None:
            extra['tier'] = int(buf.tier[i])
        sites.append(PhoxoidSite(
            site_id=i,
            position=position,
            frame=frame,
            germ=germ,
            softness=softness,
            confidence=confidence,
            extra=extra,
        ))

    field_id = field_id or _new_field_id()
    field = PhoxoidField(
        field_id=field_id,
        dimensionality=3,
        sites=sites,
        audit=AuditMetadata(),
        codebook_ref="",  # CRYPSOID splats are continuous, not codebook-quantized
    )
    field.audit = new_audit(
        operation_name=f'crypsoid.splat_buffer_to_phoxoid_field[{buf.scene_format}]',
        field=field,
        derived_from=[],
    )
    field.audit.timestamp = field.audit.timestamp  # already set by new_audit
    errors = validate_field(field)
    if errors:
        raise ValueError(f"CRYPSOID-derived field failed validation: {errors}")
    return field


def phox3d_path_to_phoxoid_field(
    path: Path,
    field_id: Optional[str] = None,
) -> PhoxoidField:
    """Convenience: load a .3dphox file and convert to PhoxoidField."""
    path = Path(path)
    # v28 render container is the most common; v25/v27 callers can pre-load
    # the SplatBuffer themselves and call splat_buffer_to_phoxoid_field
    buf = load_3dphox_v28_render(path)
    return splat_buffer_to_phoxoid_field(buf, field_id=field_id)


# ---------- Reverse direction: PhoxoidField -> SplatBuffer ----------

def phoxoid_field_to_splat_buffer(field: PhoxoidField) -> SplatBuffer:
    """Convert a PhoxoidField back to a CRYPSOID SplatBuffer.

    This is in-memory only. To write the result to a .3dphox file, use
    CRYPSOID's existing writers — but note they will lose the higher-order
    germ coefficients (chi, omega, zeta) until the v40 native germ chunk
    writer lands.

    Constraints (v0.1.0):
      - field.dimensionality must be 3 (2D fields can't directly become
        SplatBuffer; 3D promotion of 2D is a v0.2 spec feature)
      - Each site must have a 3-vector position and a 3x3 frame
      - The first two germ coefficients are read into GermBuffer.k1, k2;
        higher-order coefficients are dropped with a warning if non-zero
    """
    if field.dimensionality != 3:
        raise ValueError(
            f"phoxoid_field_to_splat_buffer requires 3D field; got "
            f"dimensionality={field.dimensionality}. 3D promotion of 2D fields "
            f"deferred to spec v0.2."
        )
    n = field.n_sites
    xyz = np.zeros((n, 3), dtype=np.float32)
    quats = np.zeros((n, 4), dtype=np.float32)
    scales = np.zeros((n, 3), dtype=np.float32)
    opacities = np.zeros(n, dtype=np.float32)
    sh_dc = np.zeros((n, 3), dtype=np.float32)
    tier = np.zeros(n, dtype=np.uint8)
    has_tier = False
    k1 = np.zeros(n, dtype=np.float32)
    k2 = np.zeros(n, dtype=np.float32)
    higher_order_dropped = 0

    for i, s in enumerate(field.sites):
        xyz[i] = s.position
        quats[i] = _rotation_matrix_to_quat(s.frame)
        scales[i] = s.softness[:3]
        k1[i] = s.germ.coeffs[0]
        k2[i] = s.germ.coeffs[1]
        if any(abs(s.germ.coeffs[c]) > 1e-6 for c in range(2, 5)):
            higher_order_dropped += 1
        opacities[i] = float(s.extra.get('opacity', 1.0))
        if 'sh_dc' in s.extra:
            sh_dc[i] = np.asarray(s.extra['sh_dc'], dtype=np.float32)[:3]
        if 'tier' in s.extra:
            tier[i] = int(s.extra['tier'])
            has_tier = True

    if higher_order_dropped > 0:
        # Stderr warning, not an exception — v0.1.x SplatBuffer can't carry these
        print(
            f"phoxoid_field_to_splat_buffer: {higher_order_dropped}/{n} sites "
            f"had non-zero chi/omega/zeta coefficients dropped (CRYPSOID v0.1.x "
            f"GermBuffer doesn't carry higher-order terms; v0.2+ pending)",
            file=sys.stderr,
        )

    return SplatBuffer(
        n=n,
        xyz=xyz, scales=scales, quats=quats,
        opacities=opacities, sh_dc=sh_dc,
        sh_rest=None,
        tier=tier if has_tier else None,
        germ=GermBuffer(k1=k1, k2=k2),
        correction=None,
        source=field.field_id,
        scene_format='phoxoid_field_v0.1.0',
    )


def phoxoid_field_to_phox3d_path(field: PhoxoidField, path: Path) -> Path:
    """Write a PhoxoidField to a .3dphox file.

    DEFERRED to v0.2 of the integration spec.

    The .3dphox v25/v27/v28 writers in CRYPSOID do not yet write the v40
    native germ chunks (germ_5coef_f16, germ_index_u32) needed to
    losslessly round-trip a PhoxoidField. Writing through the existing
    writers would silently drop higher-order germ coefficients
    (chi, omega, zeta), violating the audit guarantee.

    To unblock this:
      1. CRYPSOID lands the v40 writer per docs/v40_native_germ_chunks_spec.md
      2. This function is reimplemented as:
           buf = phoxoid_field_to_splat_buffer(field)
           write_3dphox_v40(buf, path)   # not yet implemented
         with audit operation appended for the write.

    For v0.1.0 callers can:
      - convert via phoxoid_field_to_splat_buffer + write through v25/v28
        writers, accepting the loss of higher-order germ coefficients
      - serialize the field to JSON via phoxoid_field.write_json (lossless)
        as an interim alternative
    """
    raise NotImplementedError(
        "phoxoid_field_to_phox3d_path requires the v40 native germ chunk "
        "writer (CRYPSOID v0.4+). For v0.1.0 use phoxoid_field_to_splat_buffer "
        "(in-memory) or phoxoid_field.write_json (lossless JSON sidecar)."
    )
