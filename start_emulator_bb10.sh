#!/usr/bin/env bash
# Start the prepared BB10 Passport simulator in its own QEMU GTK window.
set -euo pipefail

BB10_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
BB10_STATE_NAME="${BB10_STATE_NAME:-vmvga-gtk-passport}"
[[ "$BB10_STATE_NAME" =~ ^[a-zA-Z0-9_-]+$ ]] || { echo '잘못된 BB10_STATE_NAME입니다.' >&2; exit 1; }
BB10_STATE="$BB10_ROOT/emulator/state/$BB10_STATE_NAME"
BB10_CONTAINER=bb10-vmvga-3d
BB10_IMAGE="${BB10_RUNTIME_IMAGE:-bb10-vmvga-gui:v1}"
BB10_CONTROL="$BB10_ROOT/tools/simulator.mjs"

case "${1:-}" in
    --help|-h)
        echo '사용법: ./start_emulator_bb10.sh [--check]'
        echo 'QEMU GTK 창을 열고 Passport 1440×1440 프로필을 자동 선택합니다.'
        echo '내부 해상도는 유지하며 창에만 50%로 표시합니다. Ctrl+C 또는 창 닫기로 종료합니다.'
        echo '--check: 실행 의존성과 준비된 파일만 확인합니다.'
        exit 0 ;;
    --check|'') ;;
    *) echo '지원하지 않는 인수입니다. --help를 확인하세요.' >&2; exit 1 ;;
esac

for BB10_TOOL in node python3 docker qemu-img xauth tesseract flock; do
    command -v "$BB10_TOOL" >/dev/null || { echo "필요한 명령이 없습니다: $BB10_TOOL" >&2; exit 1; }
done
[[ "${DISPLAY:-}" =~ ^:[0-9]+(\.[0-9]+)?$ ]] || { echo '로컬 그래픽 세션에서 실행하세요. X11 DISPLAY가 필요합니다.' >&2; exit 1; }
docker info >/dev/null 2>&1 || { echo 'Docker daemon에 접근할 수 없습니다. 실행 상태와 사용자 권한을 확인하세요.' >&2; exit 1; }
docker image inspect "$BB10_IMAGE" >/dev/null 2>&1 || { echo "실행 이미지가 없습니다: $BB10_IMAGE (HOWROUSE.md 참고)" >&2; exit 1; }
for BB10_FILE in \
    emulator/images/10.3.1.2558/BlackBerry10Simulator.vmdk \
    emulator/evidence/guest/passport-zoom50.raw \
    emulator/evidence/guest/passport-zoom100.raw \
    emulator/lib/dxvk/usr/lib/libdxvk_d3d9.so.0; do
    [[ -f "$BB10_ROOT/$BB10_FILE" ]] || { echo "준비된 파일이 없습니다: $BB10_FILE (HOWROUSE.md 참고)" >&2; exit 1; }
done
if [[ "${1:-}" == --check ]]; then
    echo 'BB10 Passport 실행 의존성·이미지·라이브러리 확인 완료.'
    exit 0
fi

mkdir -p "$BB10_STATE"
exec 9>"$BB10_STATE/start.lock"
flock -n 9 || { echo '같은 프로필의 실행 스크립트가 이미 동작 중입니다.' >&2; exit 1; }
if [[ "$(docker container inspect --format '{{.State.Running}}' "$BB10_CONTAINER" 2>/dev/null || true)" == true ]]; then
    echo 'BB10 VM이 이미 실행 중입니다. 기존 VM을 먼저 종료하세요.' >&2
    exit 1
fi
if [[ -e "$BB10_STATE/qmp.sock" ]]; then
    echo "기존 QMP 소켓이 있습니다. 상태를 확인하세요: $BB10_STATE/qmp.sock" >&2
    exit 1
fi

BB10_LAUNCH_TOKEN="bb10-start-$$-$(date +%s%N)"
export BB10_LAUNCH_TOKEN BB10_STATE_NAME
BB10_LOG="$BB10_STATE/start.log"
BB10_VM_PID=''
bb10_owns_container() {
    [[ "$(docker container inspect --format '{{index .Config.Labels "bb10.launch-token"}}' "$BB10_CONTAINER" 2>/dev/null || true)" == "$BB10_LAUNCH_TOKEN" ]]
}
bb10_cleanup() {
    local bb10_exit=$?
    trap - EXIT INT TERM
    if [[ -n "$BB10_VM_PID" ]] && kill -0 "$BB10_VM_PID" 2>/dev/null; then
        if bb10_owns_container; then
            node "$BB10_CONTROL" stop --state "$BB10_STATE" >/dev/null 2>&1 || \
                docker stop --time 5 "$BB10_CONTAINER" >/dev/null 2>&1 || true
        else
            kill -TERM "$BB10_VM_PID" 2>/dev/null || true
        fi
        wait "$BB10_VM_PID" 2>/dev/null || true
    fi
    if [[ "$bb10_exit" != 0 && "$bb10_exit" != 130 && "$bb10_exit" != 143 ]]; then
        echo "실행에 실패했습니다. 로그: $BB10_LOG" >&2
        tail -n 15 "$BB10_LOG" >&2
    fi
    exit "$bb10_exit"
}
trap bb10_cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM

printf '\n[%s] Passport GTK start\n' "$(date -Is)" >>"$BB10_LOG"
echo 'QEMU GTK 창을 여는 중입니다. Passport 프로필을 자동으로 선택합니다.'
echo "실행 로그: $BB10_LOG"
bash "$BB10_ROOT/emulator/runtime/passport-gui.sh" >>"$BB10_LOG" 2>&1 &
BB10_VM_PID=$!
BB10_READY=false
for ((BB10_ATTEMPT=0; BB10_ATTEMPT<150; BB10_ATTEMPT++)); do
    if ! kill -0 "$BB10_VM_PID" 2>/dev/null; then
        echo 'QEMU 시작에 실패했습니다. 최근 로그:' >&2
        tail -n 20 "$BB10_LOG" >&2
        exit 1
    fi
    if [[ -S "$BB10_STATE/qmp.sock" ]] && bb10_owns_container && \
            node "$BB10_CONTROL" status --state "$BB10_STATE" >/dev/null 2>&1; then
        BB10_READY=true
        break
    fi
    sleep 0.2
done
[[ "$BB10_READY" == true ]] || { echo "QMP 준비 시간이 초과됐습니다. $BB10_LOG를 확인하세요." >&2; exit 1; }

node "$BB10_CONTROL" menu --no-reset --state "$BB10_STATE" >>"$BB10_LOG" 2>&1
node "$BB10_CONTROL" resume --state "$BB10_STATE"
node "$BB10_CONTROL" key 4 --state "$BB10_STATE"
node "$BB10_CONTROL" key ret --state "$BB10_STATE"
echo 'Passport 1440×1440 부팅을 시작했습니다. 창 표시 배율은 50%입니다.'
echo 'BB10 초기 서비스 준비에는 수 분이 걸릴 수 있습니다. 종료: Ctrl+C 또는 QEMU 창 닫기.'
wait "$BB10_VM_PID"
