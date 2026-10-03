#!/usr/bin/env bash
set -euo pipefail
repo=$(cd "$(dirname "$0")/.." && pwd)
images=${FUXI_IMAGES:-$repo/output/images}
sim=${FUXI_SIM:-$repo/../verilator-axi-testbench/build/linux-bringup/examples/fuxi/fuxi_sim}
test -x "$sim" || { echo "Set FUXI_SIM to the generated simulator executable: $sim" >&2; exit 1; }
dtb="$images/fuxi/fuxi-sim.dtb"
if [[ -n ${FUXI_CMDLINE:-} ]]; then
    mkdir -p "$repo/debug"
    run_dir=$(mktemp -d "$repo/debug/run.XXXXXX")
    cp "$dtb" "$run_dir/fuxi-sim.dtb"
    dtb="$run_dir/fuxi-sim.dtb"
    bootargs=$(fdtget -t s "$dtb" /chosen bootargs)
    fdtput -t s "$dtb" /chosen bootargs "$bootargs $FUXI_CMDLINE"
fi
exec "$sim" \
    --load "0x200=$images/fuxi-bootstub.bin" \
    --elf "$images/fw_jump.elf" \
    --load "0x80400000=$images/Image" \
    --load "0x87e00000=$dtb" \
    --max-cycles "${FUXI_MAX_CYCLES:-2000000000}" --stats "$@"
