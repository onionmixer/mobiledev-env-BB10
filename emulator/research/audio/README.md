# BB10 simulator audio comparison and optional AK4531 experiment

The stock simulator recognizes QEMU's **ES1370 PCI controller**, but its image
omits the AK4531 mixer plugin required for that controller. This is a missing
guest component, rather than evidence that QNX cannot recognize ES1370. QEMU's
Intel AC97 controller is a different PCI device and does not match the image's
fixed `audiopci` startup driver.

## Observed configuration and comparison

Original `emulator/images/10.3.1.2558/BlackBerry10Simulator.vmx`:

```text
virtualHW.version = "7"
sound.present = "TRUE"
sound.fileName = "-1"
sound.autodetect = "TRUE"
sound.pciSlotNumber = "33"
```

There is **no `sound.virtualDev` entry**. No original VMware runtime PCI
inventory was available. VMware developer Darius Davis explains that the
ES1371 device is used when this option is absent in the Workstation/Fusion
versions discussed in his 2020 post. Applying this to the 2015 BB10 image is a
source-supported inference, not a measurement of its original VMware session.
[VMware developer explanation](https://community.broadcom.com/vmware-cloud-foundation/communities/community-home/digestviewer/viewthread?CommunityKey=fb707ac3-9412-4fad-b7af-018f5da56d9f&GroupId=7171&MessageKey=52549622-507e-4670-a432-5d519b2bd854)

| Configuration | PCI controller identification | BB10 controller match | Mixer selected by actual guest code | Present in image | Status |
| --- | --- | --- | --- | --- | --- |
| Original VMware VMX | Actual PCI ID unmeasured; ES1371 inferred | ES1371 family supported | `deva-mixer-ac97.so` for ES1371 family | Yes | Consistent with intended VMware configuration |
| ES1371 family IDs explicitly accepted by BB10 | `1274:1371`, `1274:5880`, `1102:8938` | Yes | `ac97` | Yes | QEMU stock ES1370 is not this controller |
| QEMU `ES1370` | `1274:5000` | Yes | `deva-mixer-ak4531.so` | **No** | PCI attach supported; mixer loading blocks complete initialization |
| QEMU `AC97` | Intel 82801AA, `8086:2415` | **No**, not probed by `audiopci` | Would need QNX `deva-ctrl-i8x0.so` | Controller absent | Renaming an AC97 codec does not make it an ES1371 controller |

Guest `startup.sh:446` runs `io-audio ... -d audiopci` with aliases for playback
device index 1 and capture index 0. `audioman` later waits for mixer devices.
`acoustic_vmware.conf` contains software acoustic processing with `nolibrary true`;
it does not select or emulate a PCI sound controller.

REA analysis of `deva-ctrl-audiopci.so` verifies all four PCI ID probes and the
ES1370→`ak4531` / ES1371→`ac97` branches. Independent analysis of `io-audio`
verifies that `ado_mixer_dll` constructs `deva-mixer-<name>.so`, calls `dlopen`,
and rejects a missing library. It requires plugin ABI major version 5.
Evidence and pseudocode are under `emulator/evidence/guest/audio/`:
`audiopci-evidence.json`, `io-audio-evidence.json`, `ac97-evidence.json` and their
`*-analysis.json` snapshots. All REA targets were closed after export.

QNX independently documents both required mixer alternatives for this driver:
[audiopci](https://qnx.com/developers/docs/6.6.0_anm11_wf10/com.qnx.doc.neutrino.utilities/topic/d/deva-ctrl-audiopci.so.html),
[AK4531 mixer](https://qnx.com/developers/docs/6.6.0_anm11_wf10/com.qnx.doc.neutrino.utilities/topic/d/deva-mixer-ak4531.so.html).

## Minimal runtime probe

For ES1370, add a host audio backend and its controller, for example:

```text
-audiodev pa,id=audio0 -device ES1370,audiodev=audio0
```

For reproducible PCM evidence, use a WAV backend instead of PulseAudio:

```text
-audiodev wav,id=audio0,path=/absolute/experimental-output.wav -device ES1370,audiodev=audio0
```

These options are a probe, **not a claim that the unmodified guest plays sound**.
The original image is expected to fail loading `deva-mixer-ak4531.so`. A compatible
plugin must be supplied through an explicitly configured guest library path
before testing actual playback. Do not overwrite the shipped AC97 plugin.
The launcher and live VM were not changed by this investigation.
[QEMU audio options](https://www.qemu.org/docs/master/system/qemu-manpage.html)

The guest contains `/usr/bin/wave` and these useful PCM assets:

* `/usr/share/sounds/system_master_volume_reference.wav`: stereo, 16-bit, 48 kHz.
* `/usr/share/sounds/video_record_stop_sound.wav`: mono, 16-bit, 48 kHz.

Once the hardware card has initialized, a direct PCM probe is:

```sh
wave -a0:0 -v -p30 /usr/share/sounds/system_master_volume_reference.wav
```

Observe successful PCM/mixer creation (`/dev/snd/pcmC0D0p`, mixer C0D0), absence of
the mixer load error, progress/completion from `wave`, ES1370 DMA/interrupt
activity, and non-silent captured PCM. A host WAV file merely existing, a PCI
device appearing, or a process returning zero is insufficient playback evidence.
System notification/volume-preview playback additionally exercises `audioman`
routing and its preferred-device aliases.

## Optional source-built plugin: experimental, not enabled

`emulator/evidence/audio-experiment/deva-mixer-ak4531.so` was built with the current
SDK for x86. **It has not been loaded or played through the guest.** Its manifest
records that limitation. No deployment or guest startup changes were made.

The SDK provides `mixer/ak4531_dll.h`, but omits `audio_driver.h` and `ado_mixer.h`.
`dds_abi.h` therefore declares only documented opaque DDS functions; their names
and argument usage were cross-checked against the shipped AC97 mixer. Every DDS
import of the new ELF is exported by the actual guest `io-audio`. This supports
an experimental runtime test, not a promise of complete ABI compatibility.

The implementation passes actual register writes to the existing controller's
write callback, powers/releases reset, routes both DAC paths, creates the PCM
and Master mixer groups, and implements stereo attenuation/mute with a write
shadow. It does not manufacture successful DMA or replace the existing PCM
controller. Capture routing/gain is intentionally unimplemented and unverified.

`test_codec.c` checks callback register writes, power/clock/routing setup,
attenuation inversion, mute preservation, clamping and shadow readback. These
host tests passed; target compilation and ELF import verification passed.

```sh
bash emulator/research/audio/build.sh
```

QNX 32-bit host tools may need execution outside this workspace's syscall
sandbox. The build stages only its own sources in `/tmp` and copies its ELF to
`emulator/evidence/audio-experiment/`. Existing simulator files are never written.

The driver callback layout comes directly from the installed SDK header.
Opaque API declarations use the
[QNX mixer API reference](https://www.qnx.com/developers/docs/6.4.1/ddk_en/audio/api-ref.html),
including [playback groups](https://www.qnx.com/developers/docs/6.4.1/ddk_en/audio/api-ref/ado_mixer_playback_group_create.html)
and [PCM elements](https://www.qnx.com/developers/docs/6.4.1/ddk_en/audio/api-ref/ado_mixer_element_pcm1.html).
Register meanings were checked against the installed Linux 6.8 AK4531 driver
and [its upstream source](https://github.com/torvalds/linux/blob/v6.8/sound/pci/ak4531_codec.c);
the experimental register/control implementation was written separately.
The examined OpenQNX mirror supplied no audio DDS implementation to build.

One additional emulator limitation: the exact pinned QEMU fork's `es1370.c`
does not model the analog codec register gain/mute controls. It transfers PCM
through its audio backend independently. The plugin sends valid codec writes,
but analog master-volume changes alone need not affect QEMU output. Per-stream
software mixing/volume and host backend controls must be tested separately.
[Pinned QEMU source](https://github.com/winboat-org/qemu-helios/blob/helios-11.1.1/hw/audio/es1370.c)
