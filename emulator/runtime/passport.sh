#!/usr/bin/env bash
set -eo pipefail
BB10_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)"
export BB10_STATE_NAME=vmvga-3d-zoom50
export BB10_READONLY_BACKING="$BB10_ROOT/emulator/evidence/guest/passport-zoom50.raw"
[[ -f "$BB10_READONLY_BACKING" && -f "$BB10_ROOT/emulator/state/$BB10_STATE_NAME/BB10.qcow2" ]] || {
    echo 'Prepared Passport zoom experiment is missing. See docs/emulator/COMPATIBILITY.ko.md.' >&2
    exit 1
}
echo "Use the boot menu Keyboard [1440x1440] option (4). Display: ${BB10_DISPLAY:-vnc}"
exec bash "$BB10_ROOT/emulator/runtime/run.sh" 3d "${1:-kvm}"
