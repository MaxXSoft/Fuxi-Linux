#!/usr/bin/env python3
"""Record inputs and artifact hashes beside the build output."""
import hashlib
import json
import os
from pathlib import Path
import platform
import subprocess
import sys

repo = Path(__file__).resolve().parent.parent
output = Path(sys.argv[1]).resolve()

def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()

def git(*args):
    # Trust only this explicitly selected checkout across Lima's UID mapping.
    return subprocess.check_output(['git', '-c', f'safe.directory={repo}',
                                    '-C', str(repo), *args], text=True).strip()

configs = {}
for name, pattern in [('buildroot', '.config'), ('linux', 'build/linux-*/.config'),
                      ('busybox', 'build/busybox-*/.config'),
                      ('opensbi', 'build/opensbi-*/build/platform/generic/kconfig/.config')]:
    files = list(output.glob(pattern))
    if len(files) == 1:
        dest = output / 'images' / f'{name}.config'
        dest.write_bytes(files[0].read_bytes())
        configs[name] = sha(dest)

print(json.dumps({
    'sources': json.loads((repo / 'sources.lock').read_text()),
    'integration_commit': git('rev-parse', 'HEAD'),
    'integration_dirty': bool(git('status', '--porcelain')),
    'host': platform.platform(),
    'parallel_jobs': int(os.environ.get('FUXI_JOBS', '2')),
    'output_directory': str(output),
    'config_sha256': configs,
    'artifact_sha256': {str(p.relative_to(output / 'images')): sha(p)
                       for p in sorted((output / 'images').rglob('*'))
                       if p.is_file() and p.name != 'manifest.json'},
}, indent=2) + '\n')
