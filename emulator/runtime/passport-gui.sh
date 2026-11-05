#!/usr/bin/env bash
set -euo pipefail
BB10_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)"
python3 "$BB10_ROOT/emulator/runtime/prepare-passport-native.py"
export BB10_STATE_NAME="${BB10_STATE_NAME:-vmvga-gtk-passport}"
export BB10_READONLY_BACKING="$BB10_ROOT/emulator/evidence/guest/passport-zoom100.raw"
export BB10_DISPLAY=gtk
export BB10_GTK_SCALE=0.5
echo 'QEMU GTK: full internal Passport resolution, 50% host display. Select boot option 4.'
exec bash "$BB10_ROOT/emulator/runtime/run.sh" 3d "${1:-kvm}"
