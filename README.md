# Fuxi Linux

A Buildroot external tree for booting **OpenSBI → Linux → musl/BusyBox** on
Fuxi in `verilator-axi-testbench`. The initial target is one RV32IMAC hart,
ILP32 soft-float, Sv32, 128 MiB RAM, UART console, and an initramfs built into
the kernel. No disk, network device, or U-Boot is needed.

Upstream source versions are pinned in [`sources.lock`](sources.lock) and
[`configs/fuxi_defconfig`](configs/fuxi_defconfig). Buildroot is fetched with a
depth-one commit fetch; Linux and OpenSBI use commit archives with SHA256 checks.
Buildroot supplies its matched GCC, binutils, musl and BusyBox versions. No full
Git histories or forks of these components are needed.

## Build in Linux

On Debian/Ubuntu, install dependencies once:

```sh
./scripts/install-deps.sh
./scripts/build.sh
```

`FUXI_WORK` defaults to `$HOME/fuxi-linux`; `FUXI_JOBS` defaults to 2. Keep this
workspace on a native case-sensitive Linux filesystem. The external tree may
be on a shared host mount. See [`env/README.md`](env/README.md) for the initial
Lima environment and proxy configuration.

For the existing macOS/Lima layout:

```sh
limactl start default --tty=false
limactl shell default env FUXI_PROXY=socks5h://host.lima.internal:13659 \
  bash /Users/maxxing/Programming/Fuxi-Linux/scripts/build.sh
```

The first build creates the cross toolchain. Subsequent builds reuse downloaded
archives and completed package builds. Temporary executables stay under
`$FUXI_WORK/tmp`, not `/tmp`.

Important outputs in `$FUXI_WORK/output/images`:

- `fw_jump.bin` and `.elf`: generic OpenSBI firmware.
- `Image`: Linux with its static BusyBox and test program embedded in initramfs.
- `fuxi/fuxi-sim.dtb`: Fuxi testbench hardware description.
- `fuxi-bootstub.bin` and `.elf`: reset stub setting hart ID and DTB address.
- `manifest.json` and `*.config`: resolved inputs, configuration and image hashes.

## Validate in QEMU

Run inside the builder, or set `FUXI_IMAGES` to copied images on macOS:

```sh
./scripts/smoke.py --log "$HOME/fuxi-linux/logs/qemu.log" -- \
  ./scripts/run-qemu.sh
```

The QEMU launcher uses an RV32I CPU with M/A/C, Zicsr, Zifencei, Zicntr, S/U and Sv32
enabled. QEMU generates its own device tree; its CLINT/PLIC addresses differ
from Fuxi. Both platforms use the same firmware and kernel image.

The initramfs checks fork/exec, copy-on-write, page protection and SIGSEGV,
misaligned scalar accesses, clock_gettime/nanosleep, and tmpfs file operations.
Success requires the `FUXI_LINUX_SMOKE_PASS` marker, no failure marker, and a
normal emulator exit. A firmware banner or shell prompt alone is insufficient.

For an interactive QEMU shell:

```sh
FUXI_CMDLINE=fuxi.interactive=1 ./scripts/run-qemu.sh
```

## Run on Fuxi

Build the simulator from the Linux bring-up branch of Fuxi and the testbench
with `./scripts/build-sim.sh`. It checks that both checkouts are clean and match
`sources.lock`, then explicitly selects the sibling Fuxi checkout;
`FUXI_SOURCE` and `FUXI_TESTBENCH` override those source paths. Run
`scripts/export-images.sh` inside the VM to copy the software images into this
checkout's ignored `output/images` directory and verify their hashes, then run
the simulator on the host:

```sh
./scripts/smoke.py --timeout 3600 --log debug/fuxi.log -- ./scripts/run-fuxi.sh
```

Install the simulator build dependencies described in the testbench README
(including JDK/sbt, Verilator, CMake and a C++ compiler) on that host. Software
cross-compilation remains inside Linux; the simulator can run on macOS.

`FUXI_SIM` overrides the executable path and `FUXI_IMAGES` overrides the image
directory. `FUXI_MAX_CYCLES` defaults to two billion. The simulator reset PC is
`0x200`; an ELF entry point does not change it.

Use `FUXI_CMDLINE=fuxi.interactive=1 ./scripts/run-fuxi.sh` for an interactive
BusyBox shell, then run `fuxi-smoke` and `fuxi-finish 0`. Additional command-line
arguments are placed in a copy of the DTB under `debug/`; this requires
`fdtget`/`fdtput` from the device-tree compiler package (`brew install dtc` on
macOS). The original exported image remains unchanged.

| Payload / device | Physical address |
| --- | --- |
| Reset stub | `0x00000200` |
| OpenSBI | `0x80000000` |
| Linux Image | `0x80400000` |
| DTB | `0x87e00000` |
| UART / PLIC source 10 | `0x10000000` |
| Simulation exit register | `0x10001000` |
| CLINT | `0x11000000` |
| PLIC, M context 0 / S context 1 | `0x12000000` |

The DTS advertises a 50 MHz timebase, matching the testbench's default CLINT
divider. OpenSBI's existing generic syscon reset driver writes zero to the exit
register on SBI shutdown. No custom Linux or OpenSBI device driver is required
for this wiring.

## Maintain the configuration

Use `make -C "${FUXI_WORK:-$HOME/fuxi-linux}/output" menuconfig`, `linux-menuconfig`, or
`busybox-menuconfig`, and save deliberate changes with `savedefconfig`,
`linux-update-defconfig`, or `busybox-update-config`. A saved defconfig is an
input; image-side full configurations record how Kconfig resolved it.

Do not edit `output/build` as the source of record. Put required source patches
under `board/fuxi/patches/<package>/`, or add packages under `package/`. For local
package edits, use the corresponding `*-rebuild` target before rebuilding the
rootfs and kernel. After ABI, toolchain or major kernel configuration changes,
validate in a new `FUXI_WORK` directory.

After package-specific rebuilds, run `scripts/build.sh` without arguments (or
with a final `all` target) to regenerate initramfs, Image and their manifest.
Changing a BusyBox selection can leave old applet links in an incremental
target directory; use a fresh work directory for the reproducibility check.

To collect package sources, applied patches and license manifests:

```sh
./scripts/build.sh legal-info
work=${FUXI_WORK:-$HOME/fuxi-linux}
git -C "$work/buildroot" archive --format=tar --prefix=buildroot/ HEAD \
  | gzip -n > "$work/output/legal-info/buildroot.tar.gz"
```

The extra archive supplies the Buildroot sources that `legal-info` does not
save automatically. Keep this external tree's Git revision alongside that
directory and the image manifest. No generated archives need to be committed
to this repository.

Fixed inputs make the workflow repeatable; bit-identical reproduction still
requires comparing two clean builds. Generated files, download caches and logs
are ignored by Git.
