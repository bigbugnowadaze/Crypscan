#!/usr/bin/env bash
# install_to_CRYPSOID.sh
#
# Copies the staged CRYPSOID adapter files from this crypscan checkout
# into a local CRYPSOID clone, overwriting any prior versions.
#
# Usage (from inside your crypscan checkout):
#   ./external_adapters/install_to_CRYPSOID.sh /path/to/your/CRYPSOID/clone
#
# After running, cd into your CRYPSOID clone and:
#   cd <CRYPSOID>
#   git status                 # confirm files added under tools/
#   git add tools/phoxoid_field/ tools/phoxoid_field_adapter.py tools/test_phoxoid_field_adapter.py
#   git commit -m "v0.1.0 phoxoid_field adapter — closes audit gap G1"
#   git push origin main

set -euo pipefail

if [ "$#" -ne 1 ]; then
  echo "usage: $0 <path-to-CRYPSOID-clone>" >&2
  exit 1
fi

DEST="$1"
SRC="$(cd "$(dirname "${BASH_SOURCE[0]}")/CRYPSOID" && pwd)"

if [ ! -d "$DEST" ]; then
  echo "ERROR: destination $DEST does not exist" >&2
  exit 1
fi
if [ ! -d "$DEST/tools" ]; then
  echo "ERROR: $DEST does not look like a CRYPSOID clone (no tools/ dir)" >&2
  exit 1
fi

echo "Copying staged CRYPSOID adapter files:"
echo "  from: $SRC"
echo "  to:   $DEST"
echo ""

mkdir -p "$DEST/tools/phoxoid_field"
cp -v "$SRC/tools/phoxoid_field/"*.py "$DEST/tools/phoxoid_field/"
cp -v "$SRC/tools/phoxoid_field_adapter.py" "$DEST/tools/"
cp -v "$SRC/tools/test_phoxoid_field_adapter.py" "$DEST/tools/"

echo ""
echo "Done. To verify:"
echo "  cd $DEST/tools && python3 test_phoxoid_field_adapter.py"
echo ""
echo "To commit and push:"
echo "  cd $DEST"
echo "  git add tools/phoxoid_field/ tools/phoxoid_field_adapter.py tools/test_phoxoid_field_adapter.py"
echo "  git commit -m 'v0.1.0 phoxoid_field adapter — closes audit gap G1'"
echo "  git push origin main"
