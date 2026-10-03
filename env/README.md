# Linux builder

The initial build uses the existing Lima `default` VM on macOS ARM64:

- Ubuntu 24.10 ARM64, Linux 6.11.0-19-generic
- 8 virtual CPUs, 4 GiB memory, four compiler jobs
- Native VM workspace: `/home/maxxing.linux/fuxi-linux`
- Shared configuration checkout: `/Users/maxxing/Programming/Fuxi-Linux`
- Host GCC 14.2.0, GNU Make 4.3

Run `scripts/install-deps.sh` inside a Debian/Ubuntu Linux VM with working apt
repositories. The existing Ubuntu 24.10 instance needed its apt URI changed from
`http://ports.ubuntu.com/ubuntu-ports` to
`https://old-releases.ubuntu.com/ubuntu`; its original sources were backed up as
`/etc/apt/sources.list.d/ubuntu.sources.pre-fuxi`. A new builder can use a supported
Ubuntu release with the same dependency script.

Keep `FUXI_WORK` on the VM's native, case-sensitive filesystem. Host-shared
configuration and scripts are fine; Linux source and Buildroot output should not
be extracted onto the macOS home mount. `build.sh` sets `TMPDIR` to a directory
under `FUXI_WORK`, including for configure probes and host executables.

An optional SOCKS proxy can be supplied as `FUXI_PROXY`. In Lima, use
`socks5h://host.lima.internal:13659`; on the host the corresponding address is
`socks5h://127.0.0.1:13659`. This setting is used for Git and the pinned GitHub
archives and Buildroot's archive download transport. The latter is a small curl
adapter for Buildroot's wget backend; Buildroot still verifies the archive hashes.

These inputs and a successful rerun establish build reproducibility at the
workflow level. Bit-identical output needs two clean builds and artifact hash
comparison; enabling `BR2_REPRODUCIBLE` alone does not establish that property.
