#!/usr/bin/env bash
# Run in the Linux builder; the destination may be on a shared macOS mount.
set -euo pipefail
repo=$(cd "$(dirname "$0")/.." && pwd)
work=${FUXI_WORK:-$HOME/fuxi-linux}
destination=${1:-$repo/output/images}
test -f "$work/output/images/manifest.json"
mkdir -p "$destination"
cp -a "$work/output/images/." "$destination/"
python3 - "$destination" <<'PY'
import hashlib, json, sys
from pathlib import Path
root = Path(sys.argv[1])
manifest = json.loads((root / 'manifest.json').read_text())
for name, expected in manifest['artifact_sha256'].items():
    actual = hashlib.sha256((root / name).read_bytes()).hexdigest()
    if actual != expected:
        raise SystemExit(f'Hash mismatch after export: {name}')
print(f'Exported and verified {len(manifest["artifact_sha256"])} files: {root}')
PY
