# Spec — `phoxoid_field` dtype (v0.1.0)

**Status:** **APPROVED v0.1.0** — partnership review 2026-05-04
**Authored:** 2026-05-04
**Closes:** audit gap **G1** (the keystone gap from `AUDIT_B1_cross_tree_integration.md`)
**Scope:** the single canonical data type representing a *phoxoidal field* — a collection of catastrophe-germ sites — that CRYPSOID, Aurexis, and the phoxoidal carrier can all produce and consume. v0.1.0 is minimal core; extensions deferred.

**Resolved decisions on §8 open questions:**
- Q1 — `basis` **locked** to `"pearcey5"` for v0.1.0. No alternatives admitted.
- Q2 — Field-level confidence is **derived/computed on demand**, not stored.
- Q3 — 3D ↔ 2D projection **deferred to v0.2**. v0.1.0 trees interoperate through Aurexis FieldBundle conversion.
- Q4 — Dtype name **remains `phoxoid_field` pending B-3**. Will be renamed if/when naming settles.

---

## 1. Why this exists

Today the three trees share a thematic vocabulary (catastrophe germs, predicates, sites, frames) but no interface. CRYPSOID writes germ-bearing splats into `.3dphox`. Aurexis Workbench operates on FieldBundles of generic image dtypes. The phoxoidal carrier outputs decoded codewords + positions. None of these is consumable by the others without manual translation, which means the dual-fiber substrate exists in citation only.

This spec defines **one in-memory representation, one wire format, and a small set of boundary functions per tree** — the surgical interface that turns three slices into one substrate.

---

## 2. Data structure (canonical in-memory)

```
PhoxoidField {
    version          : str             # "v0.1"
    field_id         : str             # short unique handle (e.g. UUIDv7)
    dimensionality   : int             # 2 or 3 (2D fields are degenerate 3D with z=0)
    sites            : [PhoxoidSite]
    codebook_ref     : str             # SHA-256 of canonical codebook serialization;
                                        # empty string means "free-form, not codebook-quantized"
    audit            : AuditMetadata
}

PhoxoidSite {
    site_id     : int                  # local index within the field
    position    : float[D]             # D = dimensionality; canvas-pixel or world units
    frame       : float[D, D]          # local rotation; identity = axis-aligned
    germ        : GermCoefficients
    softness    : float[4]             # σ_a, σ_b, σ_n, τ (CRYPSOID Layer 2); for 2D σ_n unused
    confidence  : ConfidenceState
    extra       : dict                 # optional: tier label, appearance, opacity, neighbor_glue
}

GermCoefficients {
    basis    : str                     # canonical: "pearcey5" → (κ₁, κ₂, χ, ω, ζ) per
                                        # CRYPSOID `thesis_digest.md` §2 Layer 2
    coeffs   : float[5]                # raw coefficients in basis order
    quality  : float                   # fit residual or classifier margin in [0, 1]
}

AuditMetadata {
    derived_from : [str]               # field_ids of source fields (if a composition)
    operations   : [str]               # ordered list of operation names applied
    hash_chain   : [str]               # SHA-256 anchors after each operation
    timestamp    : str                 # ISO 8601 of field creation
}

ConfidenceState = enum {
    "TRUST", "HOLD", "DOWNGRADE", "REJECT", "NEED_MORE_EVIDENCE"
}
```

**Wire format (v0.1):** JSON for everything except `coeffs` and `frame`, which are inlined as base64-encoded little-endian float32 blobs to avoid float-print drift. Fully diff-able as text. Binary wire format deferred to v0.2 if scale demands it.

---

## 3. Required boundary functions per tree

### CRYPSOID adapter (~1 day work, mostly mechanical)

```
phox3d_to_phoxoid_field(scene_path: Path) -> PhoxoidField
phoxoid_field_to_phox3d(field: PhoxoidField, out: Path) -> None
```

Maps each `.3dphox` splat to a PhoxoidSite. Default ConfidenceState=TRUST for raw renders. Tier label goes in `extra`. Round-trips losslessly for v0.1 fields with single-codebook splats.

### Aurexis Workbench adapter (~3 days, includes 4 new operators)

```
field_bundle_to_phoxoid_field(bundle: FieldBundle, extractor: GermExtractor) -> PhoxoidField
phoxoid_field_to_field_bundle(field: PhoxoidField) -> FieldBundle
```

Plus four new vision operators registered in the predicate runtime:

```
dominant_germ_type(field) -> label             # "fold" | "cusp" | "swallowtail" | "umbilic" | "flat" | "mixed"
germ_signature_match(field, target_germ, tolerance:scalar) -> bool
field_curvature_axis(field) -> label           # "x" | "y" | "z" | "none"
compose_fields(a, b) -> PhoxoidField           # sheaf composition with cohomology check
```

These operators consume PhoxoidField directly. Independence-Ratio scoring extends to them by the existing Workbench machinery without core changes.

### Phoxoidal carrier adapter (~1 day, derives from existing spike-9B output)

```
carrier_decode_to_phoxoid_field(result: DecodeResult, params: EncodeParams) -> PhoxoidField
phoxoid_field_to_carrier(field: PhoxoidField, payload: bytes, out: Path) -> EncodeInfo
```

The decoder already produces `germ_positions`, `decoded_codewords`, and per-germ `median_payload_ncc`. Conversion is mechanical: each decoded germ becomes a PhoxoidSite with `position`, `frame=identity_2D`, `germ.coeffs` from the codebook entry, and `quality = NCC_margin`.

---

## 4. Type-checking and composition rules

- Fields with different `dimensionality` cannot be composed directly. A 2D-to-3D promotion (lifting a 2D field into a plane in 3D) and a 3D-to-2D projection (rendering a 3D field through a camera) must be explicit operations with their own audit entries.
- `compose_fields(a, b)` requires `codebook_ref` to either match or one to be empty.
- Confidence states propagate by **worst-of-with-one-step-downgrade-per-composition**:
  - `compose(TRUST, TRUST)   = HOLD`           (one downgrade tick per composition)
  - `compose(TRUST, HOLD)    = DOWNGRADE`
  - `compose(TRUST, REJECT)  = REJECT`
  - `compose(any, NEED_MORE_EVIDENCE) = NEED_MORE_EVIDENCE`
- A predicate operating on a PhoxoidField must declare its required `dimensionality` and `basis` in its DSL signature; the type checker rejects mismatches at install time.

---

## 5. Audit guarantees

- Every PhoxoidField carries an immutable derivation chain.
- Each operation that produces a new field appends to `audit.operations` and emits a new SHA-256 anchor.
- The pair `(field_id, hash_chain)` is sufficient to reproduce the field from its source data.
- Replay: a `verify(field, source_inputs)` operation rebuilds the field from sources and confirms hash anchors match.

This is the v0.1 of audit gap **G5** (unified audit format) — the data structure is in place; specific verification tooling is v0.2.

---

## 6. What v0.1 unlocks (closes gaps G1, G2, parts of G4 and G5)

When implemented across all three trees:

| Capability | Was | Becomes |
|---|---|---|
| CRYPSOID render's germ structure → Aurexis predicates | manual data shuffling | `phox3d_to_phoxoid_field` → predicate runtime |
| Two phoxoidal carriers composed cohomologically | not possible | `compose_fields(carrier_a_field, carrier_b_field)` |
| 2D image → CRYPSOID 3D scene → predicate query | three disconnected pipelines | one PhoxoidField passed through the three adapters |
| Audit trail across the substrate | three local formats | one AuditMetadata propagated through all operations |

---

## 7. Explicitly NOT in v0.1

- The mathematics of `compose_fields`'s cohomological consistency check. v0.1 ships the interface; semantics formalized in B-2.
- The full predicate calculus over PhoxoidField. v0.1 ships 4 starter operators; vocabulary expansion is partnership work, not spec work.
- A binary wire format. JSON-with-blobs adequate for v0.1 scale (≤ ~10⁵ sites). v0.2 if needed.
- Streaming / large-field support (≥ 10⁶ sites). Deferred.
- Codebook lifecycle (versioning, evolution). v0.1 references codebooks by hash; lifecycle in v0.2+.
- "Predicate-as-payload" carrier (gap G3) — independent of the spec; can be built once v0.1 is in.
- Cross-modal validation (gap G6) — needs v0.1 + at least 2 of the 4 new Aurexis operators built.

---

## 8. Open questions for partnership review

1. **Lock `basis` to `"pearcey5"` for v0.1, or admit alternatives?** Locking simplifies the type system. Admitting future-proofs but pushes ambiguity into every operator's type signature. **Recommendation: lock.**

2. **Field-level confidence in addition to per-site?** Currently per-site only. A field-level summary (e.g., median or worst-case) would simplify predicate composition. **Recommendation: add as derived (computed on demand from sites + audit), not stored.**

3. **3D-2D projection: should v0.1 ship the canonical projection, or defer entirely?** Without it, CRYPSOID-to-carrier handoff requires a custom adapter. **Recommendation: defer to v0.2; CRYPSOID and the carrier interoperate through Aurexis's bundle-conversion in v0.1.**

4. **Naming.** This spec uses "phoxoid_field" because it's accurate but inherits the confused naming across the trees. If B-3 (naming) settles on a different name for the substrate, this dtype should rename to match. **Recommendation: don't rename until B-3 lands.**

---

## 9. Total integration cost (estimate)

| Tree | Work | Effort |
|---|---|---|
| CRYPSOID | one adapter file (~150 LoC) | 1 day |
| Aurexis | dtype registration + 4 operators + IR-scoring extension | 3 days |
| Phoxoidal carrier | one adapter file (~100 LoC); reuses spike-9B decode result | 1 day |
| Cross-tree integration test | one PhoxoidField round-trip across all three adapters | 1 day |
| **Total** | | **~1 week**, distributed |

After implementation, the trees stop being parallel slices and become genuine subsystems of one substrate. B-3 (naming) and B-2 (formalization) become tractable on a substrate that empirically exists.

---

## 10. What this spec is not

- **Not a build.** It's the contract that lets the partnership (Bug + Vince + Claude as needed) split the build work cleanly across the trees.
- **Not the full integration.** v0.1 closes G1 fully and G2/G4/G5 partially. G3, G6, G7 remain.
- **Not the manifesto's substrate.** That substrate also requires the formalization work (B-2). v0.1 makes that formalization possible by giving it something concrete to formalize against.
- **Not locked.** Partnership review feedback expected; v0.1 is a draft pending Bug + Vince approval before any tree starts implementing.

---

**Next decision:** approve the spec as v0.1, request changes, or reject. If approved, the three adapter implementations can proceed in parallel — they don't need to wait for each other once the spec is fixed.
