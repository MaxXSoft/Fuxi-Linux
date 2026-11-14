#!/usr/bin/env python3
"""Export built images and verify the copied artifact hashes."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil

repo = Path(__file__).resolve().parent.parent
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('destination', nargs='?', help='destination directory (default: output/images in this checkout)')
args = parser.parse_args()

work = Path(os.environ.get('FUXI_WORK') or Path.home() / 'fuxi-linux')
source = (work / 'output/images').resolve()
root = Path(args.destination) if args.destination else repo / 'output/images'
root = root.resolve()
if root == source or source in root.parents:
    raise SystemExit(f'Destination must be outside the source images: {root}')
if not (source / 'manifest.json').is_file():
    raise SystemExit(f'Missing build manifest: {source / "manifest.json"}')
root.mkdir(parents=True, exist_ok=True)

for path in source.rglob('*'):
    if path.is_file():
        target = root / path.relative_to(source)
        target.parent.mkdir(parents=True, exist_ok=True)
        # Shared macOS mounts need file contents, not Linux owner/timestamp metadata.
        shutil.copyfile(path, target)

manifest = json.loads((root / 'manifest.json').read_text())
for name, expected in manifest['artifact_sha256'].items():
    actual = hashlib.sha256((root / name).read_bytes()).hexdigest()
    if actual != expected:
        raise SystemExit(f'Hash mismatch after export: {name}')

print(f'Exported and verified {len(manifest["artifact_sha256"])} files: {root}')
