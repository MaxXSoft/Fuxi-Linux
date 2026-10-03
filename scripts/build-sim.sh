#!/usr/bin/env bash
set -euo pipefail
repo=$(cd "$(dirname "$0")/.." && pwd)
fuxi=${FUXI_SOURCE:-$repo/../Fuxi}
tb=${FUXI_TESTBENCH:-$repo/../verilator-axi-testbench}
fuxi=$(cd "$fuxi" && pwd)
tb=$(cd "$tb" && pwd)
python3 - "$repo/sources.lock" "$fuxi" "$tb" <<'PY'
import json, subprocess, sys
sources = json.load(open(sys.argv[1]))
for name, path in zip(('fuxi', 'testbench'), sys.argv[2:]):
    def git(*args):
        return subprocess.check_output(['git', '-C', path, *args], text=True).strip()
    expected = sources[name]['commit']
    if git('rev-parse', 'HEAD') != expected or git('status', '--porcelain'):
        raise SystemExit(f'{name}: use a clean checkout of {expected} at {path}; '
                         'update sources.lock deliberately when testing another revision')
PY
mkdir -p "$tb/debug/linux-bringup/tmp"
export TMPDIR="$tb/debug/linux-bringup/tmp"
cd "$tb"
cmake --preset fuxi -B build/linux-bringup -DAXI_TB_FUXI_SOURCE_DIR="$fuxi"
cmake --build build/linux-bringup --target fuxi_sim -j "${FUXI_SIM_JOBS:-2}"
printf 'Simulator: %s\n' "$tb/build/linux-bringup/examples/fuxi/fuxi_sim"
