#!/usr/bin/env bash

set -euo pipefail

# Debian/Ubuntu builder. The configured apt repositories must be reachable.
sudo apt-get update
sudo env DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
  build-essential bash bc bison flex gawk rsync cpio unzip wget file bzip2 \
  xz-utils zstd patch perl python3 git curl ca-certificates libncurses-dev \
  libssl-dev libelf-dev device-tree-compiler qemu-system-misc cmake ninja-build pkg-config
