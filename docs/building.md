# Building and maintaining the software

Run the commands below from the repository root on Linux. On macOS, use a
Linux VM such as Lima for cross-compilation; QEMU or a separately built Fuxi
simulator can run on the host.

## Build environment

On a supported Debian/Ubuntu installation, install the host dependencies once:

```sh
./scripts/install-deps.sh
git -c core.symlinks=true submodule update --init third_party/buildroot
./scripts/build.sh
```

The script uses the checkout in `third_party/buildroot` and leaves its Git
revision unchanged. Initialize or update the submodule explicitly after
checking out a revision of this repository that changes its pin.
Buildroot requires real symbolic links; the explicit `core.symlinks=true`
also handles hosts whose global Git configuration disables them. An existing
checkout created with links disabled must have its links restored before use.

The first build creates a cross toolchain. Later builds reuse downloaded
sources and completed package builds. Keep `FUXI_WORK` on a native,
case-sensitive Linux filesystem: extracted package sources and build outputs
must not live on a case-insensitive macOS shared mount. The repository itself
can be on a shared mount that supports executable files and symbolic links.

The default two parallel jobs limit memory use during toolchain compilation.
For more parallelism, provide more RAM; 8 GiB is a useful starting point.
Memory-constrained builders may also need swap. Build and configure probes
use `$FUXI_WORK/tmp` for temporary files and executables.

| Variable | Default | Purpose |
| --- | --- | --- |
| `FUXI_WORK` | `$HOME/fuxi-linux` | Build workspace containing `output`, `downloads`, `logs` and `tmp` |
| `FUXI_JOBS` | `2` | Buildroot package build parallelism |
| `FUXI_PROXY` | unset | Optional curl proxy for package downloads |
| `FUXI_MIRROR` | `https://sources.buildroot.net` | Primary package source mirror; set empty to try upstream first |

For example:

```sh
FUXI_WORK="$HOME/fuxi-linux" FUXI_JOBS=2 ./scripts/build.sh
```

`FUXI_PROXY` is passed to curl by `scripts/download.py`, the transport adapter
used by Buildroot's wget backend. Buildroot still manages source caching and
hash verification. Use a proxy address reachable from the builder; a Lima VM
can reach a proxy on the macOS host through `host.lima.internal`.

Git submodule initialization is a separate operation. If Git also needs the
proxy, pass it explicitly:

```sh
git -c core.symlinks=true -c http.proxy="$FUXI_PROXY" \
  submodule update --init third_party/buildroot
```

## Outputs and export

The build writes these files under `$FUXI_WORK/output/images`:

| File | Purpose |
| --- | --- |
| `fw_jump.bin`, `fw_jump.elf` | Generic OpenSBI firmware |
| `Image` | Linux with the BusyBox root filesystem and smoke program in its initramfs |
| `rootfs.cpio` | The root filesystem archive |
| `fuxi/fuxi-sim.dtb` | Device tree for the Fuxi simulation platform |
| `fuxi-bootstub.bin`, `fuxi-bootstub.elf` | Simulation reset stub that passes hart ID and DTB address to OpenSBI |
| `manifest.json`, `*.config` | Actual source revisions/URLs, dirty state, resolved configurations and image hashes |

The reset stub assumes the simulator has already loaded the firmware, kernel
and DTB into memory. It does not initialize a physical board or load images
from Flash. A board boot loader supplies those operations separately.

To copy the images out of a VM, run this inside the builder:

```sh
./scripts/export-images.py /path/to/shared/images
```

Without an argument, the destination is this checkout's ignored
`output/images` directory. The script checks the copied artifacts against the
manifest. Set `FUXI_IMAGES` to that directory when running on another host.

## Configuration and package changes

`configs/fuxi_defconfig` selects the architecture, toolchain, packages and
image formats. It also points to the Linux and BusyBox configurations under
`board/fuxi/`, the DTS, root filesystem overlay and extra package hashes.

Use the generated output Makefile to edit and save configuration changes:

```sh
out="${FUXI_WORK:-$HOME/fuxi-linux}/output"
make -C "$out" menuconfig
make -C "$out" savedefconfig
make -C "$out" linux-menuconfig
make -C "$out" linux-update-defconfig
make -C "$out" busybox-menuconfig
make -C "$out" busybox-update-config
```

Save deliberate changes before calling `scripts/build.sh` again: the script
reapplies `fuxi_defconfig` on each invocation. The checked-in files are inputs;
the full configurations beside the images show how Kconfig resolved them.

Keep source patches under `board/fuxi/patches/<package>/` and local packages
under `package/`. Do not use edits in `output/build` as the source of record.
For example, after changing the local smoke program:

```sh
./scripts/build.sh fuxi-smoke-rebuild all
```

After package-specific rebuilds, finish with `all` (or run `build.sh` without
arguments) to regenerate the root filesystem, kernel and manifest. For ABI,
toolchain or major kernel configuration changes, use a new `FUXI_WORK`.
Changing BusyBox selections can leave old applet links in an incremental
target directory, so validate such changes with a clean build too.

Buildroot's commit pins the versions of GCC, binutils, musl and BusyBox. To
upgrade Buildroot, update and commit the submodule pointer. To change Linux
or OpenSBI, update the archive URL in `configs/fuxi_defconfig` and its `.hash`
file under `board/fuxi/patches`. Linux and `linux-headers` use the same source
archive here, so update both hash files together. Forced download hash
checking remains enabled.

Local package `.hash` files record the license text hashes used by
`legal-info`. They do not register packages: `Config.in`, `external.mk` and
the package `.mk` files provide their configuration and build rules.

## Source and license collection

```sh
./scripts/build.sh legal-info
work=${FUXI_WORK:-$HOME/fuxi-linux}
git -C third_party/buildroot archive --format=tar --prefix=buildroot/ HEAD \
  | gzip -n > "$work/output/legal-info/buildroot.tar.gz"
```

Keep this external tree's revision and the image manifest with the collected
sources, patches and license manifests. The additional archive preserves the
Buildroot sources themselves. Use a clean checkout when collecting a release;
`git archive` includes committed content only.

## Repository formatting

The repository's `.editorconfig` uses two-space indentation for C, assembly,
Shell, DTS and linker scripts, four spaces for Python, and Buildroot's Tab
conventions for `.mk` and `Config.in`. Python embedded in Shell heredocs also
uses four spaces. The Buildroot submodule retains its upstream formatting.
