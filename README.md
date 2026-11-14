# Fuxi Linux

A Buildroot external tree for building **OpenSBI → Linux → musl/BusyBox** for
Fuxi. The default configuration targets one RV32IMAC hart, ILP32 soft-float,
Sv32, 128 MiB RAM and a serial console, with the root filesystem embedded in
the kernel as an initramfs.

Buildroot is pinned as a [submodule](third_party/buildroot). Linux and OpenSBI
source archives are selected in [the defconfig](configs/fuxi_defconfig) and
verified against the hashes in [board/fuxi/patches](board/fuxi/patches).
Processor RTL and simulator builds are managed separately.

## Build and test

From this checkout on Debian/Ubuntu Linux:

```sh
git -c core.symlinks=true submodule update --init third_party/buildroot
./scripts/install-deps.sh
./scripts/build.sh
./scripts/smoke.py --log "${FUXI_WORK:-$HOME/fuxi-linux}/logs/qemu.log" -- \
  ./scripts/run-qemu.sh
```

`FUXI_WORK` defaults to `$HOME/fuxi-linux` and must be on a native,
case-sensitive Linux filesystem. `FUXI_JOBS` defaults to 2. Images and their
manifest are written to `$FUXI_WORK/output/images`.

To use an independently built Fuxi simulator, supply its executable path:

```sh
FUXI_IMAGES=/path/to/images ./scripts/run-fuxi.sh /path/to/fuxi_sim
```

The output includes OpenSBI firmware, Linux `Image`, `rootfs.cpio`, the
simulation DTB and a simulation reset stub. Board-specific boot loaders and
device trees are managed by the board project.

- [Build environment, configuration and source maintenance](docs/building.md)
- [QEMU and Fuxi validation, simulator interface and reproducibility](docs/testing.md)

## License

Unless otherwise stated, original Fuxi-Linux code and documentation are
licensed under the [GNU General Public License, version 3 only](LICENSE)
(`GPL-3.0-only`).

Third-party components, including the Buildroot submodule and downloaded
Linux, OpenSBI, toolchain and userspace sources, retain their respective
licenses. See [source and license collection](docs/building.md#source-and-license-collection)
for collecting their sources and license information.

Copyright (C) 2026 MaxXing.
