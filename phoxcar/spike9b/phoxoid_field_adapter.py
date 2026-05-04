"""Carrier-side adapter for phoxoid_field v0.1.0.

Per SPEC_phoxoid_field_v0.1.md §3 (Phoxoidal carrier adapter):

    carrier_decode_to_phoxoid_field(decode_result, params) -> PhoxoidField
    phoxoid_field_to_carrier(field, payload, out_path) -> EncodeInfo

The carrier already produces, at decode time:
  - germ_positions (canonical canvas pixel coords)
  - decoded_codewords (codebook indices, per germ)
  - median_payload_ncc (proxy for per-germ quality)

Mapping to PhoxoidField:
  - dimensionality = 2
  - one PhoxoidSite per germ position
  - position = (cx, cy) from grid_index_to_pixel
  - frame = identity 2x2 (carrier germs are axis-aligned in the canvas)
  - germ.coeffs = codebook[decoded_codeword] mapped to raw theta
  - germ.quality = NCC value
  - softness = (sigma, sigma, 0, 1.0) — 2D, sigma_n unused, tau placeholder
  - confidence = TRUST if NCC margin high, HOLD otherwise
  - codebook_ref = SHA-256 of canonical codebook serialization
"""
from __future__ import annotations
import hashlib
import sys
from pathlib import Path

import numpy as np

# Ensure phoxoid_field package is importable
_HERE = Path(__file__).resolve().parent
_REPO_ROOT = _HERE.parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from phoxoid_field import (
    PhoxoidField, PhoxoidSite, GermCoefficients, AuditMetadata,
    ConfidenceState, write_json, read_json, validate_field,
)
from phoxoid_field.audit import new_audit

# Local imports from spike-9B
sys.path.insert(0, str(_HERE))
from basis import OrthoBasis
from codebook import design_codebook
from encoder import (
    EncodeParams, MANIFEST_INDICES, PILOT_INDICES, PAYLOAD_INDICES,
    grid_index_to_pixel,
)


def _codebook_sha256(codebook: np.ndarray) -> str:
    """Canonical SHA-256 of the codebook for codebook_ref."""
    h = hashlib.sha256()
    h.update(codebook.astype(np.float32).tobytes())
    return h.hexdigest()


def _confidence_from_ncc(ncc: float, margin: float = 0.0) -> str:
    """Map NCC + margin to a confidence state."""
    if ncc >= 0.85 and margin >= 0.1:
        return ConfidenceState.TRUST
    if ncc >= 0.7:
        return ConfidenceState.HOLD
    if ncc >= 0.5:
        return ConfidenceState.DOWNGRADE
    if ncc >= 0.3:
        return ConfidenceState.NEED_MORE_EVIDENCE
    return ConfidenceState.REJECT


def carrier_decode_to_phoxoid_field(
    decode_result,                              # spike9b.decoder.DecodeResult
    decoded_codewords_per_germ: list[int],
    germ_positions: list[tuple[int, int]],
    germ_nccs: list[float],
    params: EncodeParams,
    field_id: str | None = None,
) -> PhoxoidField:
    """Build a PhoxoidField from a successful (or partial) carrier decode.

    Args:
        decode_result: spike9b decoder result (used for top-level metadata
            like sha256_ok, transform).
        decoded_codewords_per_germ: codebook indices per germ position.
        germ_positions: canonical canvas (cx, cy) per germ.
        germ_nccs: NCC value per germ (the soft-decode quality).
        params: encode params (sigma, half_size, amp, etc.).
        field_id: optional override; auto-generated if None.

    Returns:
        PhoxoidField (validated).
    """
    import uuid
    if field_id is None:
        field_id = f"phox-{uuid.uuid4().hex[:12]}"

    # Build OrthoBasis + codebook (deterministic from params)
    basis = OrthoBasis.build(params.half_size, params.sigma)
    codebook = design_codebook(
        basis, n_codewords=params.n_codewords, seed=params.codebook_seed,
    )
    codebook_sha = _codebook_sha256(codebook)

    # Identity frame for 2D carrier germs
    frame_2d = np.eye(2, dtype=np.float32)
    # Softness (sigma, sigma, sigma_n=0 for 2D, tau=1.0 placeholder)
    softness = np.array([params.sigma, params.sigma, 0.0, 1.0], dtype=np.float32)

    sites = []
    for site_id, ((cx, cy), cw_idx, ncc) in enumerate(
        zip(germ_positions, decoded_codewords_per_germ, germ_nccs)
    ):
        # Recover raw theta coefficients for this codeword
        c_ortho = codebook[cw_idx]
        theta_raw = (basis.M_to_raw @ c_ortho).astype(np.float32)
        germ = GermCoefficients(
            coeffs=theta_raw,
            quality=float(min(max(ncc, 0.0), 1.0)),
        )
        confidence = _confidence_from_ncc(ncc)
        sites.append(PhoxoidSite(
            site_id=site_id,
            position=np.array([cx, cy], dtype=np.float32),
            frame=frame_2d.copy(),
            germ=germ,
            softness=softness.copy(),
            confidence=confidence,
            extra={
                'carrier_codeword_index': int(cw_idx),
                'canvas_grid_xy': [int(cx), int(cy)],
            },
        ))

    # Build the field with placeholder audit, then attach real audit
    field = PhoxoidField(
        field_id=field_id,
        dimensionality=2,
        sites=sites,
        audit=AuditMetadata(),
        codebook_ref=codebook_sha,
    )
    extra = {}
    if hasattr(decode_result, 'sha256_ok'):
        extra['sha256_ok'] = bool(decode_result.sha256_ok)
    if hasattr(decode_result, 'pose_ok'):
        extra['pose_ok'] = bool(decode_result.pose_ok)
    if hasattr(decode_result, 'pilot_calibration'):
        extra['pilot_calibration'] = decode_result.pilot_calibration
    field.sites[0].extra.setdefault('decode_summary', extra) if sites else None

    field.audit = new_audit(
        operation_name='carrier.decode',
        field=field,
        derived_from=[],
    )
    errors = validate_field(field)
    if errors:
        raise ValueError(f"carrier-derived field failed validation: {errors}")
    return field


def carrier_decode_full_field(decoded_dict: dict, params: EncodeParams,
                                  decode_result=None) -> PhoxoidField:
    """Convenience wrapper accepting the dict from spike9b.decoder.decode_full.

    decoded_dict structure (from spike10's decode_full or analogous):
      {
        'rectified_corrected': np.ndarray,
        'germ_indices': list[int],
        'germ_positions': list[(int, int)],
        'decoded_codewords': list[int],
      }
    """
    # NCCs aren't always carried; default to a reasonable placeholder if missing
    nccs = decoded_dict.get('germ_nccs',
                              [0.85] * len(decoded_dict['germ_positions']))
    return carrier_decode_to_phoxoid_field(
        decode_result=decode_result,
        decoded_codewords_per_germ=decoded_dict['decoded_codewords'],
        germ_positions=decoded_dict['germ_positions'],
        germ_nccs=nccs,
        params=params,
    )
