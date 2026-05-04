#!/usr/bin/env bash
# install_to_Aurexis.sh
#
# Copies the staged Aurexis adapter files from this crypscan checkout
# into a local Aurexis clone (your fork at bigbugnowadaze/Aurexis).
#
# Usage (from inside your crypscan checkout):
#   ./external_adapters/install_to_Aurexis.sh /path/to/your/Aurexis/clone
#
# After running, cd into your Aurexis clone and:
#   cd <Aurexis>
#   git remote set-url origin https://github.com/bigbugnowadaze/Aurexis.git  # if needed
#   git status
#   git add 07_VISION_SUBSTRATE/aurexis_workbench/phoxoid_field/
#   git add 07_VISION_SUBSTRATE/aurexis_workbench/vision_ops_phoxoid.py
#   git add 07_VISION_SUBSTRATE/data/vision/vocab_phoxoid.aurex
#   git commit -m "v0.1.0 phoxoid_field operators + vocab"
#   git push origin <branch>

set -euo pipefail

if [ "$#" -ne 1 ]; then
  echo "usage: $0 <path-to-Aurexis-clone>" >&2
  exit 1
fi

DEST="$1"
SRC="$(cd "$(dirname "${BASH_SOURCE[0]}")/Aurexis" && pwd)"

if [ ! -d "$DEST" ]; then
  echo "ERROR: destination $DEST does not exist" >&2
  exit 1
fi
if [ ! -d "$DEST/07_VISION_SUBSTRATE/aurexis_workbench" ]; then
  echo "ERROR: $DEST does not look like an Aurexis clone (no 07_VISION_SUBSTRATE/aurexis_workbench/ dir)" >&2
  exit 1
fi

echo "Copying staged Aurexis adapter files:"
echo "  from: $SRC"
echo "  to:   $DEST"
echo ""

mkdir -p "$DEST/07_VISION_SUBSTRATE/aurexis_workbench/phoxoid_field"
cp -v "$SRC/07_VISION_SUBSTRATE/aurexis_workbench/phoxoid_field/"*.py "$DEST/07_VISION_SUBSTRATE/aurexis_workbench/phoxoid_field/"
cp -v "$SRC/07_VISION_SUBSTRATE/aurexis_workbench/vision_ops_phoxoid.py" "$DEST/07_VISION_SUBSTRATE/aurexis_workbench/"

mkdir -p "$DEST/07_VISION_SUBSTRATE/data/vision"
cp -v "$SRC/07_VISION_SUBSTRATE/data/vision/vocab_phoxoid.aurex" "$DEST/07_VISION_SUBSTRATE/data/vision/"

echo ""
echo "Done. Files staged in your Aurexis clone."
echo ""
echo "FOR VINCE (or you, after he reviews):"
echo "  - The new dtype 'phoxoid_field' is registered at runtime via"
echo "    vision_ops_phoxoid.register_phoxoid_dtype(). Long-term, add"
echo "    'phoxoid_field' to fields.py VALID_DTYPES."
echo "  - The 4 operators register via vision_ops_phoxoid.register_phoxoid_ops()."
echo "    This should be called from vision_ops.register_all() once approved,"
echo "    OR called separately by phoxoid-aware CLI entry points."
echo "  - The bundle adapters (field_bundle_to_phoxoid_field /"
echo "    phoxoid_field_to_field_bundle) ship as STUBS marked '# NOTE for Vince'."
echo "    Final shape needs partnership input on what FieldBundle conventions"
echo "    predicates expect."
echo ""
echo "To commit and push:"
echo "  cd $DEST"
echo "  git remote set-url origin https://github.com/bigbugnowadaze/Aurexis.git  # if not already done"
echo "  git checkout -b phoxoid-field-v0.1.0  # or your preferred branch"
echo "  git add 07_VISION_SUBSTRATE/aurexis_workbench/phoxoid_field/ \\"
echo "          07_VISION_SUBSTRATE/aurexis_workbench/vision_ops_phoxoid.py \\"
echo "          07_VISION_SUBSTRATE/data/vision/vocab_phoxoid.aurex"
echo "  git commit -m 'v0.1.0 phoxoid_field operators + vocab — closes G2'"
echo "  git push origin phoxoid-field-v0.1.0"
