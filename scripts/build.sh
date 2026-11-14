#!/usr/bin/env bash
# Run inside Linux, with the work directory on a case-sensitive native disk.

set -euo pipefail

repo=$(cd "$(dirname "$0")/.." && pwd)
br="$repo/third_party/buildroot"
work=${FUXI_WORK:-$HOME/fuxi-linux}
jobs=${FUXI_JOBS:-2}

test "$(uname -s)" = Linux || { echo 'Run this script in Linux (for example, Lima).' >&2; exit 1; }
test -f "$br/Makefile" || {
  echo 'Initialize Buildroot with: git -c core.symlinks=true submodule update --init third_party/buildroot' >&2
  exit 1
}

mkdir -p "$work"/{tmp,logs,downloads}
work=$(cd "$work" && pwd)
export TMPDIR="$work/tmp"
out="$work/output"

make -C "$br" O="$out" BR2_EXTERNAL="$repo" BR2_DL_DIR="$work/downloads" fuxi_defconfig
make -C "$out" BR2_DL_DIR="$work/downloads" BR2_JLEVEL="$jobs" \
  BR2_PRIMARY_SITE="${FUXI_MIRROR-https://sources.buildroot.net}" \
  BR2_WGET="python3 $repo/scripts/download.py" "$@" 2>&1 | tee "$work/logs/build.log"

full_build=false
if [[ $# = 0 ]]; then full_build=true; fi
for target in "$@"; do
  if [[ $target = all ]]; then full_build=true; fi
done

if $full_build; then
  "$repo/scripts/manifest.py" "$out" > "$out/.manifest.json.new"
  mv "$out/.manifest.json.new" "$out/images/manifest.json"
fi
