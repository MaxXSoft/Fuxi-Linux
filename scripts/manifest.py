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

def git(path, *args):
    # Trust only this explicitly selected checkout across Lima's UID mapping.
    return subprocess.check_output(['git', '-c', f'safe.directory={path}',
                                    '-C', str(path), *args], text=True).strip()

configs = {}
resolved = {}
for name, pattern in [('buildroot', '.config'), ('linux', 'build/linux-*/.config'),
                      ('busybox', 'build/busybox-*/.config'),
                      ('opensbi', 'build/opensbi-*/build/platform/generic/kconfig/.config')]:
    files = list(output.glob(pattern))
    if len(files) != 1:
        raise SystemExit(f'Expected exactly one {name} configuration, found {len(files)}: {pattern}')
    resolved[name] = files[0]

buildroot = repo / 'third_party/buildroot'
sources = {
    'buildroot': {
        'url': git(repo, 'config', '--file', '.gitmodules',
                   'submodule.third_party/buildroot.url'),
        'commit': git(buildroot, 'rev-parse', 'HEAD'),
        'dirty': bool(git(buildroot, 'status', '--porcelain')),
    },
}
config = dict(line.split('=', 1) for line in resolved['buildroot'].read_text().splitlines()
              if line.startswith('BR2_') and '=' in line)
for name, symbol in [('linux', 'BR2_LINUX_KERNEL_CUSTOM_TARBALL_LOCATION'),
                     ('opensbi', 'BR2_TARGET_OPENSBI_CUSTOM_TARBALL_LOCATION')]:
    sources[name] = {'archive': json.loads(config[symbol])}
for name, path in resolved.items():
    dest = output / 'images' / f'{name}.config'
    dest.write_bytes(path.read_bytes())
    configs[name] = sha(dest)

print(json.dumps({
    'sources': sources,
    'integration_commit': git(repo, 'rev-parse', 'HEAD'),
    'integration_dirty': bool(git(repo, 'status', '--porcelain')),
    'host': platform.platform(),
    'parallel_jobs': int(os.environ.get('FUXI_JOBS', '2')),
    'output_directory': str(output),
    'config_sha256': configs,
    'artifact_sha256': {str(p.relative_to(output / 'images')): sha(p)
                       for p in sorted((output / 'images').rglob('*'))
                       if p.is_file() and p.name != 'manifest.json'},
}, indent=2) + '\n')
