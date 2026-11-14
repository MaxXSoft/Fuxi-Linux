#!/usr/bin/env python3
"""Compare the complete set of boot artifacts from two build directories."""

import argparse
import hashlib
import json
from pathlib import Path
import sys

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('first', type=Path, help='first output/images directory')
parser.add_argument('second', type=Path, help='second output/images directory')
args = parser.parse_args()

names = ['Image', 'fw_jump.bin', 'fw_jump.elf', 'rootfs.cpio',
         'fuxi/fuxi-sim.dtb', 'fuxi-bootstub.bin', 'fuxi-bootstub.elf']
rows = []
for name in names:
    digests = []
    for root in (args.first, args.second):
        path = root / name
        if not path.is_file():
            parser.error(f'missing artifact: {path}')
        digests.append(hashlib.sha256(path.read_bytes()).hexdigest())
    rows.append({'artifact': name, 'equal': digests[0] == digests[1],
                 'first_sha256': digests[0], 'second_sha256': digests[1]})

print(json.dumps(rows, indent=2))
sys.exit(0 if all(row['equal'] for row in rows) else 1)
