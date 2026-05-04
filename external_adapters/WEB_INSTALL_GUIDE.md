# Foolproof Web Install Guide — `phoxoid_field` v0.1.0

**For:** Bug, working only in GitHub web UI (no local clones, no terminal).
**Time:** ~15 minutes total.
**What you'll do:** download a ZIP, then use GitHub's web "Upload files"
twice (once for CRYPSOID, once for Aurexis).
**What you'll end up with:** all three repos (crypscan, CRYPSOID, Aurexis)
having the v0.1.0 phoxoid_field integration.

---

## Part 0 — sanity checklist

Before you start, confirm these in your browser:

- ✅ You can see https://github.com/bigbugnowadaze/Crypscan
- ✅ You can see https://github.com/bigbugnowadaze/CRYPSOID
- ✅ You can see https://github.com/bigbugnowadaze/Aurexis (the fork you made)

If any of those 404, fix that first before proceeding.

---

## Part 1 — Download the staging ZIP from crypscan

1. Go to:
   **https://github.com/bigbugnowadaze/Crypscan/tree/claude/phase-0-v5-handoff-Sx50S**
2. Click the green **`<> Code`** button (top right of the file list).
3. Click **Download ZIP**.
4. The download is named something like `Crypscan-claude-phase-0-v5-handoff-Sx50S.zip`.
5. **Extract the ZIP** by double-clicking it (Windows/Mac handle this natively).
   You'll get a folder named like `Crypscan-claude-phase-0-v5-handoff-Sx50S`.
6. Open that folder in your file explorer.
7. Inside, navigate into `external_adapters/`. You should see:
   ```
   external_adapters/
     ├── Aurexis/
     ├── CRYPSOID/
     ├── README.md
     ├── install_to_Aurexis.sh        (won't be used in web flow; ignore)
     ├── install_to_CRYPSOID.sh       (won't be used in web flow; ignore)
     └── integration_test_phoxoid_field.py
   ```

**Keep this folder open in your file explorer.** You'll drag from it twice.

---

## Part 2 — Install adapter into CRYPSOID (web UI)

You'll upload **3 items** into CRYPSOID's `tools/` folder:
the `phoxoid_field/` subfolder, `phoxoid_field_adapter.py`, and
`test_phoxoid_field_adapter.py`.

### 2.1 — Navigate to CRYPSOID's tools folder on GitHub

1. Go to: **https://github.com/bigbugnowadaze/CRYPSOID**
2. Click on the **`tools`** folder.
3. You should see existing files like `crypsorender/`, `phoxbench/`, `eval_metrics.py`, etc.

### 2.2 — Open the upload page

1. Above the file list, click **`Add file`** dropdown → **Upload files**.
2. You'll see a drag-and-drop area: *"Drag additional files here to add them to your repository, or choose your files."*

### 2.3 — Drag the three items into the upload area

In your file explorer (the extracted ZIP folder), navigate to:
```
external_adapters/CRYPSOID/tools/
```

You should see exactly three items there:
- `phoxoid_field/` (a folder)
- `phoxoid_field_adapter.py`
- `test_phoxoid_field_adapter.py`

**Select all three** (Ctrl-A or Cmd-A inside that folder, or drag-select)
and **drag them into the GitHub upload area**.

GitHub will start uploading. You should see all the files appear:
```
phoxoid_field/__init__.py
phoxoid_field/core.py
phoxoid_field/wire.py
phoxoid_field/audit.py
phoxoid_field/compose.py
phoxoid_field/typecheck.py
phoxoid_field/VENDOR_INFO.py
phoxoid_field_adapter.py
test_phoxoid_field_adapter.py
```

### 2.4 — Commit

Below the upload area:

1. **Commit message** (top text box): paste this:
   ```
   v0.1.0 phoxoid_field adapter — closes audit gap G1
   ```
2. **Optional description** (bottom text box, can skip).
3. Make sure the radio button **"Commit directly to the `main` branch"** is selected.
4. Click the green **`Commit changes`** button.

GitHub will commit and refresh you back to `tools/`. Confirm you now see
**`phoxoid_field`**, **`phoxoid_field_adapter.py`**, and
**`test_phoxoid_field_adapter.py`** in the listing.

✅ **CRYPSOID part done.**

---

## Part 3 — Install adapter into Aurexis (web UI)

Aurexis has TWO separate destinations because two different folder paths
are involved. You'll do uploads into two different folders.

### 3.0 — Confirm your Aurexis fork's default branch

1. Go to: **https://github.com/bigbugnowadaze/Aurexis**
2. Look at the branch dropdown near the top-left of the file list.
   It probably says **`main`** or **`master`**. **Note which one** —
   you'll commit to that branch.

### 3.1 — First upload: `aurexis_workbench/` files

You'll upload **2 items** here: the vendored `phoxoid_field/` package
and `vision_ops_phoxoid.py`.

1. From the Aurexis repo root, click into:
   ```
   07_VISION_SUBSTRATE → aurexis_workbench
   ```
2. (You should see existing files like `vision_ops.py`, `runtime.py`, `dsl.py`, etc.)
3. Click **`Add file`** → **Upload files**.
4. In your file explorer, navigate to:
   ```
   external_adapters/Aurexis/07_VISION_SUBSTRATE/aurexis_workbench/
   ```
5. **Select these 2 items** and drag them into the GitHub upload area:
   - `phoxoid_field/` (the folder)
   - `vision_ops_phoxoid.py`
6. **Commit message**:
   ```
   v0.1.0 phoxoid_field operators (part 1/2 — workbench module)
   ```
7. Make sure radio button is on **`Commit directly to the main branch`**
   (or master if that's your default).
8. Click **`Commit changes`**.

### 3.2 — Second upload: `data/vision/` vocab file

1. Click the Aurexis repo name (top breadcrumb) to go back to root.
2. Click into:
   ```
   07_VISION_SUBSTRATE → data → vision
   ```
3. (You should see existing `vocab.aurex` and other vocab data.)
4. Click **`Add file`** → **Upload files**.
5. In your file explorer, navigate to:
   ```
   external_adapters/Aurexis/07_VISION_SUBSTRATE/data/vision/
   ```
6. **Select** `vocab_phoxoid.aurex` and drag it into GitHub.
7. **Commit message**:
   ```
   v0.1.0 phoxoid_field operators (part 2/2 — vocabulary)
   ```
8. Click **`Commit changes`**.

✅ **Aurexis part done.**

---

## Part 4 — Sanity check (web only)

In each repo's web UI, confirm the new files are there:

**CRYPSOID** — go to https://github.com/bigbugnowadaze/CRYPSOID/tree/main/tools
You should see:
- ✅ `phoxoid_field/` folder
- ✅ `phoxoid_field_adapter.py`
- ✅ `test_phoxoid_field_adapter.py`

**Aurexis** — go to https://github.com/bigbugnowadaze/Aurexis/tree/main/07_VISION_SUBSTRATE/aurexis_workbench
You should see:
- ✅ `phoxoid_field/` folder
- ✅ `vision_ops_phoxoid.py`

Then go to https://github.com/bigbugnowadaze/Aurexis/tree/main/07_VISION_SUBSTRATE/data/vision
You should see:
- ✅ `vocab_phoxoid.aurex`

If any are missing, re-do that upload step.

---

## Part 5 — Tell me when you're done

That's it. Once both forks have the files committed, ping me. The cross-tree
integration test in crypscan (`external_adapters/integration_test_phoxoid_field.py`)
already passes; we don't need to re-run anything to confirm the substrate
exists.

After you confirm, we move to **B-3 (naming the substrate)**.

---

## Troubleshooting

**"My ZIP extraction is huge / weird"** — that's normal; crypscan has all the
spike-9B and other big files. You only need the `external_adapters/`
subdirectory.

**"GitHub says my upload is too big"** — shouldn't happen at this scale (max
file ~13 KB). If it does, the connection probably hiccupped; refresh and retry.

**"I see `__pycache__` in the staged folder"** — ignore it. It's Python
bytecode and won't be uploaded (it's gitignored). If it somehow gets dragged in,
GitHub will accept it but you can delete it after upload via the web UI.

**"I can't see `phoxoid_field/` in CRYPSOID after commit"** — refresh the
browser hard (Ctrl-Shift-R). GitHub's file listing sometimes caches.

**"Did I commit to the right branch?"** — go to the file you uploaded; if
the URL has `/blob/main/` in it, you're on main. If `/blob/master/`, you're
on master. Either is fine as long as it's your default branch.

**"What if I want to revert?"** — each upload was a separate commit. In
GitHub web, go to the commit, click the `<>` icon → "Revert this commit" →
opens a PR you can merge to undo it.
