#!/usr/bin/env bash
set -euo pipefail
repo=$(cd "$(dirname "$0")/.." && pwd)
fuxi=${FUXI_SOURCE:-$repo/../Fuxi}
tb=${FUXI_TESTBENCH:-$repo/../verilator-axi-testbench}
fuxi=$(cd "$fuxi" && pwd)
tb=$(cd "$tb" && pwd)
mkdir -p "$tb/debug/linux-bringup/tmp"
export TMPDIR="$tb/debug/linux-bringup/tmp"
cd "$tb"
cmake --preset fuxi -B build/linux-bringup -DAXI_TB_FUXI_SOURCE_DIR="$fuxi"
cmake --build build/linux-bringup --target fuxi_sim -j "${FUXI_SIM_JOBS:-2}"
printf 'Simulator: %s\n' "$tb/build/linux-bringup/examples/fuxi/fuxi_sim"
