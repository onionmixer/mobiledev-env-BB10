#!/usr/bin/env bash
set -euo pipefail
BB10_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)"
BB10_GUI_SOURCE="$BB10_ROOT/emulator/build/qemu-gui/source"
bb10_fetch_pinned() {
    local bb10_dir="$1" bb10_url="$2" bb10_commit="$3"
    if [[ ! -d "$bb10_dir/.git" ]]; then
        git init -q "$bb10_dir"
        git -C "$bb10_dir" remote add origin "$bb10_url"
    fi
    if ! git -C "$bb10_dir" cat-file -e "$bb10_commit^{commit}" 2>/dev/null; then
        git -C "$bb10_dir" fetch --depth 1 origin "$bb10_commit"
    fi
    git -C "$bb10_dir" checkout --detach "$bb10_commit"
}
for BB10_DEP in keycodemapdb berkeley-softfloat-3 berkeley-testfloat-3; do
    BB10_WRAP="$BB10_GUI_SOURCE/subprojects/$BB10_DEP.wrap"
    BB10_DEP_URL="$(sed -n 's/^url = //p' "$BB10_WRAP")"
    BB10_DEP_REV="$(sed -n 's/^revision = //p' "$BB10_WRAP")"
    bb10_fetch_pinned "$BB10_GUI_SOURCE/subprojects/$BB10_DEP" "$BB10_DEP_URL" "$BB10_DEP_REV"
    BB10_DEP_PATCH_DIR="$BB10_GUI_SOURCE/subprojects/packagefiles/$BB10_DEP"
    if [[ -d "$BB10_DEP_PATCH_DIR" ]]; then
        cp -a "$BB10_DEP_PATCH_DIR/." "$BB10_GUI_SOURCE/subprojects/$BB10_DEP/"
    fi
done
bb10_fetch_pinned "$BB10_GUI_SOURCE/third_party/Vulkan-Headers" \
    https://github.com/KhronosGroup/Vulkan-Headers.git \
    8864cdc896bbc2a9b6eb36b3218fc9ef57908d77
