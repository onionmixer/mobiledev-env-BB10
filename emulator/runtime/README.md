# Isolated VMVGA runtime

This image runs the pinned QEMU/VMVGA v1.03 binary using Debian 13 libraries. The host Node.js remains the command runner for the workspace.

The binary needs a newer glibc than Ubuntu 22.04 and `virgl_renderer_resource_map_fixed`, which Debian 13's virglrenderer 1.1 does not export. The image therefore extracts the official Debian `libvirglrenderer1_1.3.0-1_amd64.deb` into `/opt/virgl13` and selects that directory through `LD_LIBRARY_PATH`. The installed system package remains 1.1; the separate package metadata and digest are retained in `/opt/virgl13-package.*`.

## Build and inspect

The Docker build context is this directory, avoiding the large SDK/VM disk directories.

```bash
cp emulator/downloads/qemu-vmvga-v1.03-x86_64.part emulator/runtime/qemu-system-x86_64
docker build -t bb10-vmvga-runtime:v1.03 emulator/runtime
docker run --rm --network=none --read-only bb10-vmvga-runtime:v1.03 --version
docker run --rm --network=none --read-only bb10-vmvga-runtime:v1.03 -device vmvga,help
```

The Dockerfile verifies the QEMU binary SHA-256. [runtime.lock.json](runtime.lock.json) records the observed image identity, source digests and checks. Full installed package versions are in `emulator/evidence/vmvga-runtime-packages.txt`; current apt repository contents may change future build results.

## Runtime inputs

- Add `-L /usr/share/qemu` for BIOS/data files. The image links SeaBIOS and `vgabios-vmware.bin` into that path.
- The initial 2D comparison uses `-device vmvga,vgamem_mb=128,3d=off,debug=on`.
- KVM requires explicitly passing `/dev/kvm` to Docker. TCG requires no KVM device.
- A writable `/tmp` tmpfs is needed for temporary/cache data when the container root is read-only.
- Existing QCOW overlays have absolute backing paths. Mount the workspace at its identical absolute path or create a new overlay whose backing path is valid inside the container.

For software Vulkan, set:

```text
VK_ICD_FILENAMES=/usr/share/vulkan/icd.d/lvp_icd.json
MESA_SHADER_CACHE_DIR=/tmp/mesa-cache
```

The observed llvmpipe device provides Vulkan 1.4.305 and the VMVGA probe's required instance/device extensions. Subsequent guest testing reached a correctly shaped BB10 home screen in the default profile. With the BB10 PCnet workaround, DHCP, BAR installation, Cascades launch, and a counter button click passed. The Passport profile still has display corruption. See [the compatibility report](../../docs/emulator/COMPATIBILITY.ko.md).

For a subsequent DXVK probe, mount `emulator/lib/dxvk` read-only and include its `usr/lib` directory in `LD_LIBRARY_PATH`, preserving `/opt/virgl13/usr/lib/x86_64-linux-gnu` first. Device options are `3d=on,vgpu=9` for the legacy SVGA3D path. DXVK must be tested with the actual guest commands before claiming GUI compatibility.

## Run the prepared guest

From the workspace root, run `npm run simulator:vmvga` (or `bash emulator/runtime/run.sh 3d`). This foreground process uses the existing Docker image and DXVK directory, a dedicated QCOW2 overlay, read-only original VMDKs, KVM access with the host device group, and software Vulkan. It creates and read-only mounts a hash-checked PCnet compatibility binary. VNC listens on `127.0.0.1:5912`; the guest HTTPS forward is `127.0.0.1:4443`. The forward alone does not imply guest readiness.

Use `node tools/simulator.mjs screenshot --state emulator/state/vmvga-3d` and `stop --state emulator/state/vmvga-3d` from a second terminal. `run.sh 2d` runs the independent comparison VM on VNC 5911. Passing `tcg` as a second argument is supported by the launcher but has not been verified with this guest/VMVGA combination.

Pass `stock` as the third argument for an unmodified PCnet comparison, e.g. `bash emulator/runtime/run.sh 3d kvm stock`. `BB10_VMVGA_DEBUG=on` enables verbose graphics logs; `BB10_TRACE_PCNET=1` enables PCnet tracing and a packet dump. Both are off by default. `BB10_STATE_NAME` chooses a separate state directory under `emulator/evidence/`; only letters, numbers, `_` and `-` are accepted.

The PCnet workaround preserves DWIO only through software reset. This is a BB10 compatibility experiment and differs from AMD's hardware specification; do not use it as a generic PCnet fix. The original binary is unchanged. The patch tool, manifest and matching source diff are described in the compatibility report.
