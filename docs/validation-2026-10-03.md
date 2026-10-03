# Linux bring-up validation — 2026-10-03

The tested system is a single RV32IMAC hart with S/U privilege, Sv32, ILP32
soft-float userspace, 128 MiB RAM and an embedded initramfs. The boot flow is
reset stub → generic OpenSBI → Linux → static musl/BusyBox. There is no disk,
network device or U-Boot in this configuration.

## Software inputs and environment

| Component | Tested revision/version |
| --- | --- |
| Buildroot | `d50fadcaeed45cbbf40fdecf82901dbb938403bd` |
| Linux | `e767a4ea70a3992c37ed604157d32f0dfbf9b1e3` / 7.3.0-rc5 |
| OpenSBI | `6ad246a1494807ee91e36ffcf60e4c30bb309d45` / v1.9 |
| GCC / binutils | 15.3.0 / 2.46.1 |
| musl / BusyBox | 1.2.6 / 1.38.0 |
| Fuxi | `00bd6718e2f7de0e5fc6fc8ef0554c1b59bbce03` |
| verilator-axi-testbench | `90855cceb415605b19f6fc9fded7c7e26993935b` |

Buildroot, Linux and OpenSBI were pinned to the upstream commits selected at
the start of the work. The other packages use that Buildroot revision's matched
versions. The configuration uses ordinary upstream packages and Buildroot's
normal package patches; there are no Fuxi-specific Linux, OpenSBI, musl or
BusyBox source patches.

Cross-compilation ran in the existing Lima `default` VM: Ubuntu 24.10 ARM64,
Linux 6.11.0-19, GCC 14.2.0, GNU Make 4.3, 8 vCPUs and 4 GiB RAM. A temporary
4 GiB swap file was enabled after GCC generation exhausted RAM with four
parallel jobs. It remains at `/home/maxxing.linux/fuxi-linux/build.swap`, with
no fstab entry. See [the builder notes](../env/README.md) for installed
dependencies, apt mirror changes and proxy use.

QEMU validation used `qemu-system-riscv32` 9.0.2 inside that VM. The launch
script enables both `sv32=true` and `mmu=true`; enabling Sv32 alone on the
selected QEMU CPU left address translation disabled. The macOS ARM64 host
runs the Verilator simulator (Verilator 5.050, CMake 4.2.1, Homebrew LLVM 23.1.1).
Build/configure executables and temporary files use native work directories,
not `/tmp`.

## Software validation and reproduction

Both independent work directories built their own cross toolchain and system:

- `/home/maxxing.linux/fuxi-linux`
- `/home/maxxing.linux/fuxi-linux-repro`

They shared downloaded archives only. Configuration refinements and the final
reset-stub reproducibility fix were rebuilt in both. A separate native Git
clone also verified that committed integration files and executable modes
matched the shared checkout used for building.

Both QEMU runs passed the guest self-checks and exited normally through SBI
shutdown. The checks cover fork/exec, copy-on-write, mmap/mprotect and a child
SIGSEGV on a read-only page, forced misaligned scalar lw/sw, monotonic time and
nanosleep, plus tmpfs file operations. The child SIGSEGV register dump in the
log is expected; the parent verifies it before reporting success.

The complete artifact comparison returned success:

| Artifact | SHA256 in both directories |
| --- | --- |
| `Image` | `7bbb8b5848cdf72b61f1dd452ec7c6ea6f5cc0b85be0b808ac0aea2224afe230` |
| `fw_jump.bin` | `241533f0f2d0236c1e72d69b13c4239421522e891af6f7516b0d90dc5ae86124` |
| `fw_jump.elf` | `7d11465aa36dcffb364d0ecf7d6c0e38b1bd98cd61200d660c85f499a5555593` |
| `rootfs.cpio` | `edbaa853e2deda875dfec540189e13fe1e4b6f240cc5f35991d904545c813854` |
| `fuxi/fuxi-sim.dtb` | `0f71f508e1cc08cfb4a1a6ce64e17bc9336287358598437344dd68f357f1913d` |
| `fuxi-bootstub.bin` | `20825057df5dfe648566adf9c6cc39d490c05506ab839ab1f77579b05d9053f2` |
| `fuxi-bootstub.elf` | `6f221a7b0d72a3d638853558b5507b609a551f8e33bb41997f75d092bd412945` |

The only initial ELF difference was a GCC temporary object filename in the
reset stub's symbol table. Compiling to a fixed `boot.o` before linking removed
it without changing executable bytes. Full Linux, BusyBox and OpenSBI configs
also matched. Buildroot configs and manifests contain directory/environment
metadata and are not expected to be byte-identical.

This establishes identical artifacts for these two work directories in the
same VM, not a cross-distribution or cross-compiler reproducibility claim.
`Image` is 21,160,052 bytes (including RISC-V section-alignment padding),
`rootfs.cpio` is 330,240 bytes, and `fw_jump.bin` is 272,080 bytes.

Package sources, applied patches and license manifests were collected under
`/home/maxxing.linux/fuxi-linux/output/legal-info`. A separate Buildroot Git
archive supplies the source that its `legal-info` target does not automatically
save. Generated files are ignored by Git.

## Final Fuxi validation

Both hardware repositories use branch `codex/linux-bringup`, at the revisions
listed above. All 100 enabled testbench CTests passed (77 Fuxi tests and 23
host/RTL tests); the pre-existing `ma_data` test remains disabled. The UART
interrupt regression now reads IIR before RHR, reproducing Linux's access
sequence: it failed with the old core and passed after the MMIO width fix.

The final simulator ran the same firmware, Image and rootfs as QEMU, using the
Fuxi DTS and reset stub:

| Run | Result | Simulated cycles | Host wall time |
| --- | --- | ---: | ---: |
| Complete Linux/userspace smoke | All checks and final marker; exit 0 | 111,638,478 | 103.91 s |
| BusyBox serial shell | `uname -m` → `riscv32`, echo marker, `fuxi-finish 0`; exit 0 | 108,302,504 | 100.61 s |

The interactive test used the public launcher with
`FUXI_CMDLINE=fuxi.interactive=1`, waited for the actual shell prompt, then sent
commands through simulator stdin. It therefore covers UART receive and PLIC
delivery as well as console output. Both runs ended through generic OpenSBI's
SBI SRST shutdown path. Wall times are bring-up observations from concurrent
runs, not a performance benchmark.

Local logs are retained in ignored directories:

- Integration: `debug/qemu-final-console.log`, `debug/qemu-repro-console.log`,
  `debug/reproduction-final.json`, `debug/clean-checkout.log`, and
  `debug/build-sim-entrypoint.log`.
- Testbench: `debug/linux-bringup/linux-mmio-final-smoke.log`,
  `debug/linux-bringup/linux-mmio-final-smoke-runner.log`, and
  `debug/linux-bringup/interactive-final/console.log`.
- Core: `debug/linux-bringup/{stage2,mstatush,satp,mmio}-{red,green}.log`
  and the corresponding generation/lint logs.

Reproduce the automatic run from this checkout with:

```sh
./scripts/smoke.py --timeout 600 --log debug/fuxi.log -- ./scripts/run-fuxi.sh
```

Exported images are in `output/images`; the native VM build outputs remain in
the two work directories above. `manifest.json` contains resolved configuration
and artifact hashes. Commits are local; publishing these branches and the
external tree is a separate step.

## Processor changes found necessary

- Platform-backed `time/timeh`, counter access controls, and a separate S-mode
  external interrupt input. Machine timer/software interrupts are handled by
  OpenSBI instead of being mirrored directly into supervisor pending bits.
- MPRV/MXR and separate instruction/data effective privilege. A directed
  regression caught a load starting before an older MSTATUS write committed;
  memory requests now respect that CSR ordering.
- A WARL-zero RV32 `mstatush`: the selected OpenSBI accesses it during early
  startup before feature probing. Unsupported high-status features remain zero.
- Refetch after a committed SATP write: Linux's Sv32 trampoline exposed younger
  physical-address instructions retiring after translation was enabled.
- Preserve MMIO byte addresses and access widths: Linux's byte read of UART
  IIR at offset two previously became a full-word read and also consumed RHR
  at offset zero, dropping the first input character. The fix carries the
  actual width through the internal SRAM interface to AXI. Byte, halfword and
  word accesses, lane selection, backpressure, errors and adjacent cached
  loads have directed coverage.

Across those implementation stages, 21 distinct core regression entrypoints
completed successfully in 35 executions, with Verilog generation and wrapper
lint at each RTL stage. This count describes staged validation, not a rerun of
all 21 at the final revision. The last commit reran nine relevant entrypoints.
Logs include red-to-green evidence for CSR/load ordering, MSTATUSH access,
the SATP transition and MMIO register side effects.

The testbench connects its existing CLINT clock and separate PLIC M/S outputs.
Its existing exit-register window is eight bytes, meeting generic OpenSBI's
minimum domain-region size; only a valid 32-bit write at offset zero exits.
The DTS uses OpenSBI's existing syscon shutdown driver. No new peripheral model
or custom Linux driver was needed.

## Boundaries

This is RTL/Verilator simulation evidence. The run does not validate FPGA/ASIC
implementation, SMP, cache coherence between harts, long-running stress, every
ISA corner case, or unrelated Linux configurations. F/D/V/H and PMP remain
unsupported; ASID is zero, page A/D updates use software handling, and unaligned
scalar accesses are handled through traps rather than new hardware support.

The current root filesystem is deliberately small and static. Networking,
block storage and broader applications should be added as separate, measured
steps after retaining these baseline checks.
