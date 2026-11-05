# Read-only BB10 simulator filesystem inspection

These bounded research readers inspect a **copy** of official simulator
10.3.1.2558. They open disk inputs with `rb`, never mount a filesystem, and never
execute extracted guest binaries. They do not provide a filesystem writer.
Keep proprietary extracted files under ignored `emulator/evidence/`; do not redistribute them.

## Reproduce extraction

Run from the repository root. The raw output is sparse (8 GiB logical size).

```sh
mkdir -p emulator/evidence/guest
qemu-img convert -f vmdk -O raw emulator/images/10.3.1.2558/BlackBerry10Simulator.vmdk emulator/evidence/guest/disk.raw
python3 emulator/research/guest/qnx6_read.py emulator/evidence/guest/disk.raw 32256 /.boot
python3 emulator/research/guest/qnx6_read.py emulator/evidence/guest/disk.raw 32256 /.boot/vmware-sdk.bin --extract emulator/evidence/guest/vmware-sdk.bin
python3 emulator/research/guest/qnx6_read.py emulator/evidence/guest/disk.raw 616896000 /var/db/dhclient-en0.leases --map
curl -L -sS --fail https://raw.githubusercontent.com/abrignoni/qnxprobe/main/qnxprobe.py -o emulator/evidence/guest/qnxprobe.py
python3 emulator/research/guest/ifs_extract.py emulator/evidence/guest/vmware-sdk.bin emulator/evidence/guest/qnxprobe.py emulator/evidence/guest/ifs
python3 emulator/research/guest/rcfs_read.py emulator/evidence/guest/disk.raw /scripts/startup.sh --extract emulator/evidence/guest/startup.sh
python3 emulator/research/guest/rcfs_read.py emulator/evidence/guest/disk.raw /usr/lib/graphics/vmware
python3 emulator/research/guest/rcfs_read.py emulator/evidence/guest/disk.raw /usr/lib/graphics/vmware/graphics_BB10Keyboard1440x1440_safe.conf --extract emulator/evidence/guest/graphics_BB10Keyboard1440x1440_safe.conf
```

`ifs_extract.py` accepts only the inspected qnxprobe source SHA-256
`266f5503a0d84224ff8135371ec557b730350498e22134fdfeb8c0a8632e4940`;
the upstream URL can change. It extracts two pure UCL decoder functions using
Python AST, without importing the application or running its top-level code.
The third-party source remains under `build/`. RCFS extraction uses the existing
host `liblzo2.so.2` through ctypes; no Python packages or kernel modules needed.
`qnx6_read.py --map` reports regular-file offsets and absolute disk byte offsets,
along with file identity and SHA-256. It supports indirect blocks, labels holes
with a null disk offset, and writes no bytes. Use only a stopped VM's converted
disposable disk copy for any later experiments; an extent map of the original
does not describe blocks changed by a running VM's copy-on-write overlay.

## Observed disk layout

MBR sector size is 512 bytes.

| Type | Start LBA | Byte offset | Sectors | Contents |
| --- | ---: | ---: | ---: | --- |
| B2 | 63 | 32256 | 128457 | Plain QNX6 boot partition, `/.boot/vmware-sdk.bin` |
| B3 | 128520 | 65802240 | 1044225 | RCFS `/base`, `rimh` wrapper then superblock at +4096 |
| B4 | 1172745 | 600445440 | 32130 | NVRAM |
| B1 | 1204875 | 616896000 | 15566985 | Plain QNX6 writable `/` |

RCFS: 14090 inodes, 32 bytes each; image size 347402240; inode offset 8192;
name pool offset 462848; data offset 696320; compression block size 16384.
The reader supports this image's uncompressed and LZO-compressed files.

Boot IFS: startup header at `0x440`, machine x86, UCL compression; stored file
3533292 bytes, imagefs 8888260 bytes. Extraction produced 73 regular files.
The independent QNX image checksum (sum of all little-endian 32-bit words) is
zero. Per-file SHA-256 values are in `emulator/evidence/guest/ifs-manifest.json`.
Boot IFS SHA-256: `9c2344a486fc8a163c86b9a34ad9488a01e836a14cc382052a01e79f0ef1d587`.

## Relevant boot behavior

* `ifs/proc/boot/set_simulator_mode` first calls `guest_info BB10DeviceType`.
  Failure falls back to the console selection menu. Passport profile machine
  names are `x86pc_BB10Keyboard1440x1440` and the `Safe` suffix variant.
* `ifs/proc/boot/mount_script` mounts USER `/dev/hd0t177` with QNX6 at `/`,
  NVRAM at `/dev/hd0t180`, and RCFS `/dev/hd0t179` read-only at `/base`.
  The binary startup script then runs `/base/scripts/startup.sh`.
* `startup.sh` line 2154 selects normal or `_safe.conf`, and runs `gpu_drv`;
  `Safe` selects `gpu_drv software`. `/base/scripts/env.override.board` sets
  `DISPLAY_VID=0x15ad`, `DISPLAY_DID=0x405` and VMware graphics directory.
* **`startup.sh` line 4340 switches the console to COM1 before starting screen.**
  It starts `devc-ser8250 -e -b 115200 0x3f8,4`, waits for `/dev/ser1`, runs
  `reopen /dev/ser1`, redirects fds 3/4, then invokes `screen -U 311:311,113`.
  A VGA image still showing `START SERVICE: screen` alone cannot establish that
  `screen` itself is the blocked call; subsequent output moves to serial.
  `WAITFOR` in `common.sh` uses a 60 second default and only warns in this call.
* Passport screen configuration requests `1536 x 1560 @ 60`, framebuffer clip
  `48,48` size `1440x1440`, pipeline 1, RGBX8888, GLES2/rotation.
* Safe mode changes `gralloc-module` from `vmware` to `default`, and removes
  `gpu-dlls=libHwGPU.so`; **it still loads `libHwWFDvmware.so` for display**.
  Safe mode therefore still requires VMware display compatibility.
* No writable USER startup hook was found in the inspected IFS/startup/env/
  common scripts. `env.override.board`, `env.performance` and `debug.sh` are
  sourced only from `/base`; `STARTUP_VARIABLES` and service variable functions
  initialize their own settings. This is limited to inspected scripts, not a
  claim that all possible QNX path-manager overrides are excluded.

Extracted driver candidates are in `emulator/evidence/guest/drivers/`: `gpu_drv`,
`screen`, `devc-ser8250`, `libHwWFDvmware.so`, `libvmwsvga.so`, `libvmwgfx.so`,
and `libHwGPU.so`. They are x86 guest binaries, for analysis only.

## Provenance and limits

* QNX6 fields checked against installed Linux 6.8 `fs/qnx6/{inode,dir}.c` and
  `include/linux/qnx6_fs.h`. Source excerpts are under `emulator/evidence/guest/`.
* IFS structures checked against installed BlackBerry SDK `sys/startup.h` and
  `sys/image.h`; UCL framing/decoder checked against
  [qnxprobe](https://github.com/abrignoni/qnxprobe) (MIT, Alexis Brignoni 2026).
* RCFS layout checked against
  [bb10root/bb10mt rcfs.pas](https://github.com/bb10root/bb10mt/blob/24c3edfe87310b38ed5c4abf348c2f2666f90fbc/rcfs.pas).
  Source was inspected, not built or executed. Independent REA analysis of the
  guest `fs-rcfs.so` by the parent agent corroborated the format.
* [QNX devc-ser8250 documentation](https://www.qnx.com/developers/docs/6.5.0SP1.update/com.qnx.doc.neutrino_utilities/d/devc-ser8250.html)
  describes `-e` as edited mode with software flow control; hardware flow control
  is unsupported in that mode. Carrier-related blocking remains a runtime
  hypothesis until observed, rather than a conclusion from the script.
* This agent's REA firmware probe was unavailable because its Binwalk provider
  was not configured. The extraction and script findings here are ordinary
  shell/static evidence; the independent parent REA findings have their own
  evidence records. No runtime test or GUI success is asserted here.

## Disposable Passport zoom experiment

`patch_simulator_zoom.py` is a separate, explicitly **experimental writer**, not
part of the read-only extraction workflow. It accepts only the pre-created path
`emulator/evidence/guest/passport-zoom50.raw`, rejects source aliases and symlinks,
checks the exact known mesa inode/extent/content hash against the stopped
`current-user.raw` reference, and defaults to printing a read-only plan.

For the specific inspected copy, `/var/pps/services@0.0.775/mesa@99.0.660` contains
only the DevAlpha `0.70` setting. The experiment appends Passport `0.50` in the
same allocated block and changes the existing inode size from 43 to 89. It
writes 89 data bytes and 8 size bytes, verifies with the independent reader, and
records old/new bytes and range hashes in `passport-zoom50-manifest.json`.
It does not allocate blocks or modify RCFS code. It refuses an already patched
object or existing manifest. A successful filesystem readback does not prove
that the simulator will honor the setting; that needs a subsequent boot test.
