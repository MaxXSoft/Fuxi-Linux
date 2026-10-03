#!/usr/bin/env bash
# Run inside Linux, with the work directory on a case-sensitive native disk.
set -euo pipefail
repo=$(cd "$(dirname "$0")/.." && pwd)
work=${FUXI_WORK:-$HOME/fuxi-linux}
jobs=${FUXI_JOBS:-2}
test "$(uname -s)" = Linux || { echo 'Run this script in Linux (for example, Lima).' >&2; exit 1; }
mkdir -p "$work"/{tmp,logs,downloads}
work=$(cd "$work" && pwd)
export TMPDIR="$work/tmp"
br="$work/buildroot"
out="$work/output"
python3 - "$repo" <<'PY'
import json, pathlib, sys
repo = pathlib.Path(sys.argv[1])
sources = json.loads((repo / 'sources.lock').read_text())
config = dict(line.split('=', 1) for line in
              (repo / 'configs/fuxi_defconfig').read_text().splitlines()
              if line.startswith('BR2_') and '=' in line)
for name, symbol in [('linux', 'BR2_LINUX_KERNEL_CUSTOM_TARBALL_LOCATION'),
                     ('opensbi', 'BR2_TARGET_OPENSBI_CUSTOM_TARBALL_LOCATION')]:
    if config.get(symbol) != json.dumps(sources[name]['archive']):
        raise SystemExit(f'{name}: sources.lock and fuxi_defconfig disagree')
PY
read -r url revision < <(python3 - "$repo/sources.lock" <<'PY'
import json, sys
s = json.load(open(sys.argv[1]))['buildroot']
print(s['url'], s['commit'])
PY
)
git_options=()
if [[ -n ${FUXI_PROXY:-} ]]; then git_options=(-c "http.proxy=$FUXI_PROXY"); fi
if [[ ! -d $br/.git ]]; then
    git init "$br"
    git -C "$br" remote add origin "$url"
fi
git -C "$br" config core.symlinks true
if ! git -C "$br" cat-file -e "$revision^{commit}" 2>/dev/null; then
    git "${git_options[@]}" -C "$br" fetch --depth=1 origin "$revision"
fi
test -z "$(git -C "$br" status --porcelain)" || { echo "Dirty Buildroot checkout: $br" >&2; exit 1; }
git -C "$br" checkout --detach "$revision"
# curl supports the optional SOCKS proxy; wget (Buildroot's default) does not.
while read -r package archive; do
    filename=${archive##*/}
    mkdir -p "$work/downloads/$package"
    if [[ ! -f $work/downloads/$package/$filename ]]; then
        curl_options=()
        if [[ -n ${FUXI_PROXY:-} ]]; then curl_options=(--proxy "$FUXI_PROXY"); fi
        curl "${curl_options[@]}" -fL --retry 3 "$archive" -o "$work/downloads/$package/$filename.part"
        mv "$work/downloads/$package/$filename.part" "$work/downloads/$package/$filename"
    fi
done < <(python3 - "$repo/sources.lock" <<'PY'
import json, sys
for name, source in json.load(open(sys.argv[1])).items():
    if 'archive' in source:
        print(name, source['archive'])
PY
)
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
