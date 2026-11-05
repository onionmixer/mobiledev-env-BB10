# QEMU 자체 GTK 창으로 Passport 실행

2026-11-05에 소스 빌드한 QEMU 11.1.1 / VMVGA v1.03으로 Passport 홈 화면을 확인했습니다. **Remmina를 사용하지 않고 QEMU의 GTK 창에서 표시하며 VNC 서버는 비활성입니다.** KVM 가속이 실제 활성인 것도 QMP로 확인했습니다.

## 해상도와 표시 배율

| 항목 | 검증한 값 |
| --- | --- |
| 게스트 앱 영역 | 1440×1440 |
| 게스트 전체 프레임버퍼 | 1536×1560: 테두리·시뮬레이터 상태줄 포함 |
| 게스트 자체 확대 | 100% |
| QEMU GTK 표시 배율 | `scale=0.5`, `zoom-to-fit=off` |
| 호스트에 보이는 앱 영역 | 720×720 |
| 호스트 전체 영상 | 768×780 |
| GTK 클라이언트 창 | 768×806: 영상 외에 메뉴 높이 26 포함 |

내부 영상을 줄여 렌더링하는 방식과 구분하기 위해 별도 USER 복사본의 Passport zoom을 `1.00`으로 설정했습니다. QMP 스크린샷의 원본 크기는 1536×1560이며, 창에서만 절반으로 보입니다. QMP `query-display-options`는 GTK와 `scale: 0.5`, `query-vnc`는 `enabled: false`를 반환했습니다.

근거: `emulator/state/vmvga-gtk-passport/display-options.json`, [내부 홈 화면 원본](../../emulator/state/vmvga-gtk-passport/internal-home.png), [GTK 창 캡처](../../emulator/state/vmvga-gtk-passport/gtk-window.png). 내부 앱 영역만 정사각형이며 메뉴·테두리까지 포함한 창은 정사각형이 아닙니다.

## 실행과 종료

현재 GTK 실행 스크립트는 `show-cursor=on`을 명시해 마우스 커서를 기본으로 표시합니다. 다음 실행부터 적용되며 QEMU 재빌드는 필요하지 않습니다.

현재 호스트에는 실행 이미지와 별도 디스크를 준비했습니다.

```bash
npm run simulator:passport:gui
```

부팅 메뉴에서 `4) BlackBerry 10 Keyboard [1440x1440]`를 선택합니다. 자동으로 기본 기기로 넘어간 경우 다른 터미널에서 다음 명령으로 다시 선택할 수 있습니다.

```bash
node tools/simulator.mjs menu --state emulator/state/vmvga-gtk-passport
node tools/simulator.mjs resume --state emulator/state/vmvga-gtk-passport
node tools/simulator.mjs key 4 --state emulator/state/vmvga-gtk-passport
node tools/simulator.mjs key ret --state emulator/state/vmvga-gtk-passport
```

화면에 마우스·키보드로 직접 입력합니다. 명시적인 종료 명령은 다음과 같습니다.

```bash
node tools/simulator.mjs stop --state emulator/state/vmvga-gtk-passport
```

기존 VNC 실행은 `npm run simulator:passport`로 보존했습니다. GTK와 VNC 실행은 같은 컨테이너 이름·배포 포트를 사용하므로 동시에 실행하지 않습니다. 앱 배포 주소는 기존과 같은 `127.0.0.1:4443`입니다. 이번 GTK 검증은 홈 화면 표시와 창 배율을 확인했으며 앱 배포 재검증을 뜻하지 않습니다.

## 빌드와 격리

[설정·소스 고정 정보](../../emulator/config/qemu-gui.lock.json)에 커밋, 패치, 실행 파일 SHA-256 및 이미지 ID를 기록했습니다. 호스트 Node와 시스템 패키지는 변경하지 않았습니다. 원본 VMDK·이전 USER 복사본을 보존하고 `passport-zoom100.raw` 및 전용 QCOW2를 별도로 사용합니다.

기존 `bb10-vmvga-runtime:v1.03` 이미지가 준비된 상태에서 재빌드합니다.

```bash
npm run setup:simulator-gui
```

이 명령은 고정 커밋의 QEMU Helios·VMVGA·qemu-windows 패치와 소프트웨어 reset 시 DWIO를 보존하는 BB10 PCnet 소스 패치를 적용합니다. 빌드 의존성은 `bb10-vmvga-gui-build:v1`, 실행 라이브러리는 `bb10-vmvga-gui:v1` 컨테이너에 설치합니다. 로그·Meson 설정·패키지 목록은 `emulator/build/qemu-gui/`에 남습니다.

GTK·PulseAudio는 활성이고 SDL 프런트엔드는 껐습니다. SDL을 링크하면 프로세스 시작 시 실제 `libSDL2`가 로드돼 VMVGA DXVK의 headless WSI shim과 충돌했습니다. GTK 전용 빌드에서 해당 충돌을 제거하고 실제 홈 화면을 확인했습니다. VirGL/virtio 3D는 이 BB10 VMware SVGA 경로에 사용하지 않습니다.

직접 창은 현재 로컬 X11 세션을 사용합니다. 해당 DISPLAY의 인증 쿠키와 소켓만 전달하며 `xhost` 접근 권한은 변경하지 않습니다. 호스트 오디오도 선택적으로 사용자 PulseAudio 소켓·쿠키만 전달합니다.

## 사운드 조사 결과

호스트 출력 경로와 게스트 드라이버를 별도로 확인했습니다.

| 구성 | BB10 드라이버·믹서 | 확인 결과 |
| --- | --- | --- |
| 원본 VMware VMX | `sound.present=TRUE`, 자동 선택, `sound.virtualDev` 없음 | VMware 실제 PCI 장치는 측정하지 못함. VMware 개발자의 기본값 설명과 이미지 구성은 ES1371 계열을 시사함 |
| VMware ES1371 계열 | `audiopci` + `deva-mixer-ac97.so` | BB10 드라이버가 해당 PCI ID를 지원하고 AC97 믹서가 이미지에 존재 |
| QEMU ES1370 `1274:5000` | `audiopci` + `deva-mixer-ak4531.so` | 컨트롤러 PCI ID는 지원하지만 **필요한 AK4531 믹서가 이미지에 없음** |
| QEMU Intel AC97 `8086:2415` | 별도의 Intel 컨트롤러 드라이버 필요 | 현재 고정된 BB10 `audiopci` 드라이버의 지원 PCI ID와 다름 |

따라서 “QNX가 ES1370을 전혀 지원하지 않는다”와 “현재 이미지에서 ES1370 재생 구성이 완성되지 않는다”를 구분해야 합니다. AC97은 코덱 규격과 컨트롤러 이름에 함께 쓰이므로, QEMU `AC97` 옵션을 켜는 것만으로 VMware ES1371과 같아지지 않습니다.

실제 GTK 시험에는 ES1370과 PulseAudio를 연결했습니다. QMP에서 `1274:5000` 카드가 보였고 호스트에 QEMU 클라이언트와 출력 스트림이 생겼습니다. 하지만 게스트는 `/dev/snd/pcmPreferredp`·`pcmPreferredc`를 기다리다 시간 초과했고, 기록된 ES1370 이벤트는 초기 형식 설정뿐이며 PCM 전송은 관찰하지 못했습니다. **게스트의 실제 사운드 재생 성공은 확인하지 못했습니다.** 호스트 스트림 존재만으로 재생 성공이라고 판단하지 않습니다.

다음 명령은 재생 성공을 보장하는 기본 설정이 아니라 진단용 카드 연결입니다.

```bash
BB10_AUDIO=es1370 BB10_TRACE_AUDIO=1 npm run simulator:passport:gui
```

이번 실행 기록은 `emulator/state/vmvga-gtk-passport/audio-check.json`, `pci.json`, `serial.log`, `qemu.log`입니다. 컨트롤러·믹서 분기와 라이브러리 로딩은 REA/Ghidra로 확인해 증거를 내보냈고 분석 세션을 닫았습니다.

[사운드 비교·근거·실험 소스](../../emulator/research/audio/README.md)에 자세히 기록했습니다. 별도로 빌드한 AK4531 믹서 실험 라이브러리는 호스트 테스트와 가져오기 심볼 검증만 통과했으며 **게스트에 적용하지 않았습니다**. 기본 실행은 사운드카드를 추가하지 않습니다. 게스트 믹서와 실제 PCM 재생을 검증하기 전에는 사운드 지원 완료로 표시하지 않습니다.
