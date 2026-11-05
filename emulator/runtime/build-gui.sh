#!/usr/bin/env bash
set -euo pipefail
cd /work/out
# Reconfigure on each build so feature changes cannot reuse stale settings.
# VMVGA's headless DXVK WSI supplies its own SDL shim. Linking real SDL into
# QEMU first prevents that shim from loading, even when using the GTK window.
/work/source/configure \
    --with-pkgversion=bb10-vmvga-gtk \
    --target-list=x86_64-softmmu --enable-kvm --enable-tcg \
    --enable-gtk --disable-sdl --enable-vnc --enable-slirp \
    --enable-pa \
    --enable-pixman --enable-opengl --enable-fdt \
    --disable-virglrenderer --disable-rust --disable-modules \
    --disable-docs --disable-tools --disable-user --disable-werror \
    --disable-download --disable-install-blobs \
    > /work/configure.log 2>&1
ninja -j "${BB10_BUILD_JOBS:-16}" qemu-system-x86_64 > /work/build.log 2>&1
cp qemu-system-x86_64 /work/qemu-system-x86_64-gtk
./qemu-system-x86_64 -display help > /work/display-help.txt 2>&1
./qemu-system-x86_64 --version > /work/version.txt
sha256sum /work/qemu-system-x86_64-gtk > /work/binary.sha256
