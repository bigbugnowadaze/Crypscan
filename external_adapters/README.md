# external_adapters/ — staged adapter files for Bug to install into the partner repos

This directory exists because Claude (the AI session producing these
files) cannot push to repositories outside of `bigbugnowadaze/crypscan`.
The work that needs to land in `bigbugnowadaze/CRYPSOID` and
`bigbugnowadaze/Aurexis` is staged here in directory structures that
mirror where the files belong inside each fork.

## Workflow

1. Make sure both forks exist on your account:
   - `bigbugnowadaze/CRYPSOID` — already exists
   - `bigbugnowadaze/Aurexis` — created via fork of `KungFury87/Aurexis`
2. Clone (or already have) local checkouts of both forks somewhere on
   your machine — e.g. `~/repos/CRYPSOID`, `~/repos/Aurexis`. Make sure
   the Aurexis clone's remote points at *your* fork:
   ```
   cd ~/repos/Aurexis
   git remote set-url origin https://github.com/bigbugnowadaze/Aurexis.git
   ```
3. From inside your local crypscan checkout, run the install scripts:
   ```
   ./external_adapters/install_to_CRYPSOID.sh ~/repos/CRYPSOID
   ./external_adapters/install_to_Aurexis.sh  ~/repos/Aurexis
   ```
4. Each script prints the exact `git add` / `git commit` / `git push`
   commands to run from inside the destination clone.

## What the staging is

```
external_adapters/
├── README.md                          # this file
├── install_to_CRYPSOID.sh             # one-shot copy script
├── install_to_Aurexis.sh              # one-shot copy script
├── CRYPSOID/                          # mirrors paths inside CRYPSOID repo
│   └── tools/
│       ├── phoxoid_field/             # vendored canonical package
│       │   ├── __init__.py
│       │   ├── core.py
│       │   ├── wire.py
│       │   ├── audit.py
│       │   ├── compose.py
│       │   ├── typecheck.py
│       │   └── VENDOR_INFO.py
│       ├── phoxoid_field_adapter.py   # SplatBuffer ↔ PhoxoidField
│       └── test_phoxoid_field_adapter.py
└── Aurexis/                           # mirrors paths inside Aurexis repo
    └── 07_VISION_SUBSTRATE/
        ├── aurexis_workbench/
        │   ├── phoxoid_field/         # vendored canonical package
        │   │   ├── __init__.py
        │   │   ├── core.py
        │   │   ├── wire.py
        │   │   ├── audit.py
        │   │   ├── compose.py
        │   │   ├── typecheck.py
        │   │   └── VENDOR_INFO.py
        │   └── vision_ops_phoxoid.py  # 4 operators + dtype registration
        └── data/
            └── vision/
                └── vocab_phoxoid.aurex  # 7 starter predicates
```

## Re-vendoring

Each fork's `phoxoid_field/` is a **vendored copy** of the canonical
package at `bigbugnowadaze/crypscan:phoxoid_field/`. When the canonical
package updates, re-run the install scripts to refresh both forks.
The `VENDOR_INFO.py` file in each vendored copy records the source
revision.

## What's done

- **CRYPSOID adapter:** complete and tested on real data
  (`outputs/v28_sh_vq_render_container.3dphox`, 763,800 splats). Forward
  direction (`splat_buffer_to_phoxoid_field`) is fully functional.
  Reverse direction (`phoxoid_field_to_splat_buffer`) is functional with
  an honest `NotImplementedError` for the .3dphox writer (waits on
  CRYPSOID v40 native germ chunks).
- **Aurexis adapter:** 4 operators registered following the existing
  `vision_ops.register_all()` convention:
  `dominant_germ_type`, `germ_signature_match`, `field_curvature_axis`,
  `compose_fields`. Sample vocabulary (`vocab_phoxoid.aurex`) has
  7 starter predicates. The bundle adapters
  (`field_bundle_to_phoxoid_field` / `phoxoid_field_to_field_bundle`)
  ship as STUBS marked `# NOTE for Vince` because their final shape
  depends on partnership conventions Claude doesn't have visibility into.

## What still needs partnership input

In `Aurexis/07_VISION_SUBSTRATE/aurexis_workbench/vision_ops_phoxoid.py`,
search for `# NOTE for Vince` — three places need his eyes:

1. **fields.py edit:** `phoxoid_field` is added to VALID_DTYPES at
   runtime via `register_phoxoid_dtype()`. Long-term, edit `fields.py`
   directly to make it permanent.
2. **register_all() integration:** the new operators register via
   `register_phoxoid_ops()`. Decide whether to call this from
   `vision_ops.register_all()` (auto-load for all CLIs) or from a
   separate phoxoid-aware entry point.
3. **Bundle adapters:** what shape of FieldBundle should
   `phoxoid_field_to_field_bundle` produce so existing predicates can
   consume the field? Currently a STUB.

## After both forks land

Come back to crypscan and run the cross-tree integration test
(`integration_test_phoxoid_field.py` — coming next) which exercises a
single PhoxoidField round-tripped across all three adapters via the
JSON wire format.
