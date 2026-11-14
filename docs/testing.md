# Testing software images

## Host script checks

```sh
python3 -m unittest discover -s tests -v
```

These checks exercise the simulator launcher and build manifest without a
cross toolchain or hardware repositories. Install `dtc`, `fdtget` and `fdtput`
to include the DTB-copy test; that test is skipped if the tools are unavailable.

## Guest checks and success criteria

The default initramfs runs checks for:

- fork/exec and copy-on-write;
- mmap/mprotect, including SIGSEGV on a write to a read-only page;
- deliberately misaligned scalar loads and stores;
- monotonic time and nanosleep;
- tmpfs file creation, copying and comparison.

The protection test deliberately faults in a child process. Its SIGSEGV
diagnostic is expected; the parent verifies the signal before reporting success.

`scripts/smoke.py` requires the `FUXI_LINUX_SMOKE_PASS` marker, no
`FUXI_LINUX_SMOKE_FAIL` marker, and a normal emulator exit with status zero.
A firmware banner or shell prompt alone is not a passing result. Logs are
written to the path passed with `--log`; the default timeout is 120 seconds.

## QEMU

After building the images on Linux:

```sh
./scripts/smoke.py --log "${FUXI_WORK:-$HOME/fuxi-linux}/logs/qemu.log" -- \
  ./scripts/run-qemu.sh
```

`run-qemu.sh` defaults to `$FUXI_WORK/output/images`, or
`$HOME/fuxi-linux/output/images` when `FUXI_WORK` is unset. To use exported
images on another host, set `FUXI_IMAGES=/path/to/images`. `QEMU` can override
the `qemu-system-riscv32` executable.

The launcher enables M/A/C, Zicsr, Zifencei, Zicntr, S/U privilege and Sv32 on
QEMU's RV32I CPU, including `mmu=true`. QEMU generates its own device tree;
its CLINT and PLIC addresses differ from the Fuxi simulation platform. It uses
the same OpenSBI and kernel images, but does not load `fuxi-bootstub.bin`.

For an interactive BusyBox shell:

```sh
FUXI_CMDLINE=fuxi.interactive=1 ./scripts/run-qemu.sh
```

Inside the guest, run `fuxi-smoke` to exercise the userspace checks and
`fuxi-finish 0` to shut down. Interactive mode does not run the automatic
initramfs test sequence or emit its final PASS marker.

## Fuxi simulator

Build the simulator independently, then pass its executable as the launcher's
first argument. No Fuxi or testbench source checkout is required here:

```sh
FUXI_IMAGES=/path/to/images ./scripts/smoke.py \
  --timeout 3600 --log debug/fuxi.log -- \
  ./scripts/run-fuxi.sh /path/to/fuxi_sim
```

`run-fuxi.sh` defaults to this checkout's `output/images` directory, populated
by `scripts/export-images.sh`. The simulator path may be absolute or relative
to the current directory. Remaining arguments are forwarded to the simulator.
`FUXI_MAX_CYCLES` defaults to two billion.

The supplied executable must support these command-line options:

- `--load ADDRESS=FILE` to preload a raw image at a physical address;
- `--elf FILE` to load the OpenSBI ELF image;
- `--max-cycles COUNT` to limit simulation cycles;
- `--stats` to print simulation statistics.

It must implement the platform described by `board/fuxi/dts/fuxi/fuxi-sim.dts`:

| Payload / device | Physical address |
| --- | --- |
| Reset stub / reset PC | `0x00000200` |
| OpenSBI | `0x80000000` |
| Linux Image | `0x80400000` |
| DTB | `0x87e00000` |
| 16550 UART / PLIC source 10 | `0x10000000` |
| Simulation exit register | `0x10001000` |
| CLINT | `0x11000000` |
| PLIC, M context 0 / S context 1 | `0x12000000` |

The RAM mapping is 128 MiB starting at `0x80000000`, and the DTS advertises a
50 MHz timebase. The simulator's timer must agree with that frequency. The
reset PC is `0x200`; loading an ELF does not replace this reset entry.

OpenSBI's generic syscon reset driver writes zero to the exit register on SBI
shutdown. The simulator must terminate normally on this write. The smoke
markers distinguish guest success from failure because SBI shutdown does not
carry the guest program's exit status.

For interactive use:

```sh
FUXI_IMAGES=/path/to/images FUXI_CMDLINE=fuxi.interactive=1 \
  ./scripts/run-fuxi.sh /path/to/fuxi_sim
```

`FUXI_CMDLINE` is appended to the kernel boot arguments in a copy of the DTB
under `debug/`. This requires `fdtget` and `fdtput` from the device-tree compiler
package; the original image remains unchanged. The same guest commands as
in QEMU provide manual checks and shutdown.

## Independent build comparison

Fixed inputs and `BR2_REPRODUCIBLE=y` support reproducible builds, but matching
output bytes must be measured. Build the same clean revision into a second
native Linux workspace with its own toolchain and output:

```sh
FUXI_WORK="$HOME/fuxi-linux-repro" ./scripts/build.sh
python3 scripts/compare-images.py "${FUXI_WORK:-$HOME/fuxi-linux}/output/images" \
  "$HOME/fuxi-linux-repro/output/images"
```

The comparison covers the kernel, firmware, root filesystem, DTB and reset
stub, including ELF files. Run the guest smoke test on both image sets too.
Manifests and full Buildroot configurations contain workspace and environment
metadata, so they are not expected to be byte-identical across directories.
Record the actual build environments when reporting results; matching builds
in one environment do not establish reproducibility across all hosts.

## Validation boundaries

These checks cover a single RV32 hart and a small static userspace. QEMU
checks the software stack; an RTL simulator additionally exercises the
processor and platform implementation used for that run. Neither substitutes
for FPGA timing checks or physical-board validation, and the smoke suite is
not exhaustive ISA, SMP, networking, storage or long-running stress coverage.

Physical boards supply their own boot loader and DTB. Enable the drivers for
their actual peripherals before reusing the kernel; the default configuration
here provides the simulation platform's 8250 UART. The simulation reset stub
and exit-register protocol are not a physical-board boot/shutdown interface.
