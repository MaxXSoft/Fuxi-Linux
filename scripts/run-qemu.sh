#!/usr/bin/env bash
set -euo pipefail
repo=$(cd "$(dirname "$0")/.." && pwd)
images=${FUXI_IMAGES:-${FUXI_WORK:-$HOME/fuxi-linux}/output/images}
qemu=${QEMU:-qemu-system-riscv32}
extra=${FUXI_CMDLINE:-}
exec "$qemu" -machine virt -cpu rv32i,m=true,a=true,c=true,zicsr=true,zifencei=true,s=true,u=true,sv32=true \
    -m 128M -smp 1 -nographic -no-reboot \
    -bios "$images/fw_jump.bin" -kernel "$images/Image" \
    -append "console=ttyS0,115200 earlycon=sbi rdinit=/init panic=-1 $extra" "$@"
