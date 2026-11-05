#!/usr/bin/env bash
set -euo pipefail
BB10_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$BB10_ROOT"
if [[ ! -d emulator/references/qemu-helios/.git ]]; then
    git clone --depth 1 --branch helios-11.1.1 https://github.com/winboat-org/qemu-helios.git emulator/references/qemu-helios
fi
if [[ ! -d emulator/references/qemu-vmvga/.git ]]; then
    git clone --depth 1 --branch v1.03 https://github.com/qemus/qemu-vmvga.git emulator/references/qemu-vmvga
fi
if [[ ! -d emulator/references/qemu-windows/.git ]]; then
    git clone --depth 1 --branch v11.2.23 https://github.com/qemus/qemu-windows.git emulator/references/qemu-windows
fi
python3 emulator/runtime/prepare-gui-source.py
bash emulator/runtime/fetch-gui-deps.sh
docker build -t bb10-vmvga-gui-build:v1 -f emulator/runtime/Dockerfile.gui emulator/runtime
cp emulator/runtime/build-gui.sh emulator/build/qemu-gui/build-entry.sh
docker run --rm --name bb10-qemu-gui-build --user "$(id -u):$(id -g)" \
    --mount "type=bind,src=$BB10_ROOT/emulator/build/qemu-gui,dst=/work" \
    bb10-vmvga-gui-build:v1 /work/build-entry.sh
mkdir -p emulator/build/qemu-gui/runtime
cp emulator/build/qemu-gui/qemu-system-x86_64-gtk emulator/build/qemu-gui/runtime/
docker build -t bb10-vmvga-gui:v1 -f emulator/runtime/Dockerfile.gui-runtime emulator/build/qemu-gui/runtime
