#!/usr/bin/env bash
set -eo pipefail
BB10_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)"
BB10_MODE="${1:-2d}"
BB10_ACCEL="${2:-kvm}"
BB10_PCNET_MODE="${3:-bb10}"
BB10_DISPLAY="${BB10_DISPLAY:-vnc}"
BB10_AUDIO="${BB10_AUDIO:-none}"
[[ "$BB10_MODE" == 2d || "$BB10_MODE" == 3d ]] || { echo 'Use 2d or 3d' >&2; exit 2; }
[[ "$BB10_ACCEL" == kvm || "$BB10_ACCEL" == tcg ]] || { echo 'Use kvm or tcg' >&2; exit 2; }
[[ "$BB10_PCNET_MODE" == bb10 || "$BB10_PCNET_MODE" == stock ]] || { echo 'Use bb10 or stock PCnet mode' >&2; exit 2; }
[[ "$BB10_DISPLAY" == vnc || "$BB10_DISPLAY" == gtk || "$BB10_DISPLAY" == sdl ]] || { echo 'Use vnc, gtk or sdl display' >&2; exit 2; }
[[ "$BB10_AUDIO" == none || "$BB10_AUDIO" == es1370 ]] || { echo 'Use none or es1370 audio' >&2; exit 2; }
if [[ "$BB10_DISPLAY" == vnc ]]; then
    BB10_RUNTIME_IMAGE="${BB10_RUNTIME_IMAGE:-bb10-vmvga-runtime:v1.03}"
else
    BB10_RUNTIME_IMAGE="${BB10_RUNTIME_IMAGE:-bb10-vmvga-gui:v1}"
    [[ "$BB10_PCNET_MODE" == bb10 ]] || { echo 'GUI image includes the BB10 PCnet source fix; use VNC for stock comparison.' >&2; exit 2; }
fi
BB10_STATE_NAME="${BB10_STATE_NAME:-vmvga-$BB10_MODE}"
[[ "$BB10_STATE_NAME" =~ ^[a-zA-Z0-9_-]+$ ]] || { echo 'Invalid BB10_STATE_NAME' >&2; exit 2; }
BB10_STATE="$BB10_ROOT/emulator/state/$BB10_STATE_NAME"
BB10_BASE="$BB10_ROOT/emulator/images/10.3.1.2558"
BB10_DISK="$BB10_STATE/BB10.qcow2"
mkdir -p "$BB10_STATE"
if [[ ! -e "$BB10_DISK" ]]; then
    qemu-img create -f qcow2 -F vmdk -b "$BB10_BASE/BlackBerry10Simulator.vmdk" "$BB10_DISK"
fi
BB10_VMVGA_DEBUG="${BB10_VMVGA_DEBUG:-off}"
[[ "$BB10_VMVGA_DEBUG" == on || "$BB10_VMVGA_DEBUG" == off ]] || { echo 'Invalid BB10_VMVGA_DEBUG' >&2; exit 2; }
BB10_VIDEO="vmvga,vgamem_mb=128,debug=$BB10_VMVGA_DEBUG,3d=off"
BB10_VNC=11
BB10_HTTPS=3443
BB10_SERIAL=3423
BB10_EXTRA=()
BB10_TRACE=()
BB10_AUDIO_ARGS=()
if [[ -n "${BB10_READONLY_BACKING:-}" ]]; then
    [[ "$BB10_READONLY_BACKING" == "$BB10_ROOT/emulator/evidence/"* && -f "$BB10_READONLY_BACKING" ]] || { echo 'Backing file must exist under workspace emulator/evidence/' >&2; exit 2; }
    BB10_EXTRA+=(--mount "type=bind,src=$BB10_READONLY_BACKING,dst=$BB10_READONLY_BACKING,readonly")
fi
if [[ -z "${BB10_QEMU_BINARY:-}" && "$BB10_PCNET_MODE" == bb10 && "$BB10_DISPLAY" == vnc ]]; then
    python3 "$BB10_ROOT/emulator/research/guest/patch_pcnet_dwio.py"
    BB10_QEMU_BINARY="$BB10_ROOT/emulator/evidence/qemu-system-x86_64-bb10-pcnet"
fi
if [[ "$BB10_AUDIO" == es1370 ]]; then
    BB10_PULSE_SOCKET="${XDG_RUNTIME_DIR:-/run/user/$(id -u)}/pulse/native"
    [[ -S "$BB10_PULSE_SOCKET" ]] || { echo 'Host PulseAudio socket is missing.' >&2; exit 2; }
    BB10_EXTRA+=(--mount "type=bind,src=$BB10_PULSE_SOCKET,dst=/tmp/bb10-pulse-native" --env PULSE_SERVER=unix:/tmp/bb10-pulse-native)
    BB10_PULSE_COOKIE="${XDG_CONFIG_HOME:-$(getent passwd "$(id -u)" | cut -d: -f6)/.config}/pulse/cookie"
    if [[ -f "$BB10_PULSE_COOKIE" ]]; then
        BB10_EXTRA+=(--mount "type=bind,src=$BB10_PULSE_COOKIE,dst=/tmp/bb10-pulse-cookie,readonly" --env PULSE_COOKIE=/tmp/bb10-pulse-cookie)
    fi
    BB10_AUDIO_ARGS+=(-audiodev pa,id=bb10-audio,server=unix:/tmp/bb10-pulse-native -device ES1370,audiodev=bb10-audio)
fi
if [[ -n "${BB10_QEMU_BINARY:-}" ]]; then
    [[ -f "$BB10_QEMU_BINARY" ]] || { echo 'BB10_QEMU_BINARY must name an existing file' >&2; exit 2; }
    BB10_EXTRA+=(--mount "type=bind,src=$BB10_QEMU_BINARY,dst=/opt/vmvga/qemu-system-x86_64,readonly")
fi
if [[ "${BB10_TRACE_PCNET:-0}" == 1 ]]; then
    BB10_TRACE+=(-trace 'enable=pcnet*' -object "filter-dump,id=bb10-netdump,netdev=net0,file=$BB10_STATE/network.pcap")
fi
if [[ "${BB10_TRACE_AUDIO:-0}" == 1 ]]; then
    BB10_TRACE+=(-trace 'enable=es1370*')
fi
if [[ "$BB10_ACCEL" == kvm ]]; then
    BB10_EXTRA+=(--device=/dev/kvm --group-add "$(stat -c '%g' /dev/kvm)")
    BB10_CPU=host
else
    BB10_CPU=max
fi
if [[ "$BB10_MODE" == 3d ]]; then
    BB10_VIDEO="vmvga,vgamem_mb=128,debug=$BB10_VMVGA_DEBUG,3d=on,vgpu=9"
    BB10_VNC=12
    BB10_HTTPS=4443
    BB10_SERIAL=4423
    BB10_EXTRA+=(--mount "type=bind,src=$BB10_ROOT/emulator/lib/dxvk,dst=$BB10_ROOT/emulator/lib/dxvk,readonly")
fi
BB10_DISPLAY_ARGS=(-display none -vnc "127.0.0.1:$BB10_VNC")
if [[ "$BB10_DISPLAY" != vnc ]]; then
    [[ "${DISPLAY:-}" =~ ^:([0-9]+)(\.[0-9]+)?$ ]] || { echo 'A local X11 DISPLAY is required.' >&2; exit 2; }
    BB10_XSOCKET="/tmp/.X11-unix/X${BASH_REMATCH[1]}"
    BB10_XAUTH="$BB10_STATE/Xauthority"
    touch "$BB10_XAUTH"
    chmod 600 "$BB10_XAUTH"
    xauth nlist "$DISPLAY" | sed 's/^..../ffff/' | xauth -f "$BB10_XAUTH" nmerge -
    [[ -s "$BB10_XAUTH" ]] || { echo 'Could not prepare scoped X11 authorization.' >&2; exit 2; }
    BB10_EXTRA+=(--mount "type=bind,src=$BB10_XSOCKET,dst=$BB10_XSOCKET,readonly"
        --mount "type=bind,src=$BB10_XAUTH,dst=/tmp/bb10.Xauthority,readonly"
        --env "DISPLAY=$DISPLAY" --env XAUTHORITY=/tmp/bb10.Xauthority --env GDK_BACKEND=x11)
    BB10_EXTRA+=(--env XDG_CACHE_HOME=/tmp/bb10-cache)
    BB10_DISPLAY_ARGS=(-display "$BB10_DISPLAY,gl=off" -vnc none)
    if [[ "$BB10_DISPLAY" == gtk ]]; then
        BB10_GTK_SCALE="${BB10_GTK_SCALE:-1.0}"
        [[ "$BB10_GTK_SCALE" == 0.25 || "$BB10_GTK_SCALE" == 0.5 || "$BB10_GTK_SCALE" == 0.75 || "$BB10_GTK_SCALE" == 1 || "$BB10_GTK_SCALE" == 1.0 ]] || { echo 'GTK scale must be 0.25, 0.5, 0.75 or 1.0.' >&2; exit 2; }
        BB10_DISPLAY_ARGS=(-display "gtk,gl=off,scale=$BB10_GTK_SCALE,zoom-to-fit=off,show-cursor=on" -vnc none)
    fi
    if [[ "$BB10_DISPLAY" == sdl ]]; then
        BB10_EXTRA+=(--env SDL_VIDEODRIVER=x11)
    fi
fi
exec docker run --rm --name "bb10-vmvga-$BB10_MODE" --network=host \
    --label "bb10.launch-token=${BB10_LAUNCH_TOKEN:-manual}" \
    --read-only --cap-drop=ALL --security-opt=no-new-privileges \
    --user "$(id -u):$(id -g)" --tmpfs /tmp:rw,exec,size=512m,mode=1777 \
    --mount "type=bind,src=$BB10_BASE,dst=$BB10_BASE,readonly" \
    --mount "type=bind,src=$BB10_STATE,dst=$BB10_STATE" \
    --env "LD_LIBRARY_PATH=/opt/virgl13/usr/lib/x86_64-linux-gnu:$BB10_ROOT/emulator/lib/dxvk/usr/lib" \
    --env VK_ICD_FILENAMES=/usr/share/vulkan/icd.d/lvp_icd.json \
    --env MESA_SHADER_CACHE_DIR=/tmp/mesa-cache --env LP_NUM_THREADS=4 \
    "${BB10_EXTRA[@]}" "$BB10_RUNTIME_IMAGE" \
    -L /usr/share/qemu -name "BB10-VMVGA-$BB10_MODE" \
    -machine pc,vmport=on -accel "$BB10_ACCEL" -cpu "$BB10_CPU" -smp 1 -m 2048 \
    -vga none -device "$BB10_VIDEO" \
    -drive "file=$BB10_DISK,if=ide,format=qcow2" \
    -netdev "user,id=net0,restrict=on,hostfwd=tcp:127.0.0.1:$BB10_HTTPS-:443" \
    -device pcnet,netdev=net0 -usb -device usb-tablet \
    "${BB10_AUDIO_ARGS[@]}" \
    "${BB10_TRACE[@]}" \
    "${BB10_DISPLAY_ARGS[@]}" \
    -qmp "unix:$BB10_STATE/qmp.sock,server=on,wait=off" \
    -serial "file:$BB10_STATE/serial.log" -monitor none \
    -pidfile "$BB10_STATE/qemu.pid" -D "$BB10_STATE/qemu.log"
