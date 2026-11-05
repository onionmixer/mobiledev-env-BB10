# 사용 방법

이 문서는 **현재 준비된 작업 공간**을 기준으로 합니다. 기능별 검증 범위는 [README](README.md), 판단 과정과 한계는 [HISTORY](HISTORY.md)를 함께 확인하세요.

## 1. 호스트와 SDK 확인

작업 공간 루트에서 실행합니다. 호스트 Node를 교체하거나 구버전 Node를 별도로 설치하지 않습니다.

```bash
node --version
npm run doctor
```

SDK 기본 경로는 Docker입니다. 원본 SDK 이미지의 IDE·SSH·supervisor를 실행하지 않고 CLI 도구만 사용합니다. 호스트 XFS의 큰 inode 번호 때문에 오래된 32비트 도구가 파일을 읽지 못했던 문제는 컨테이너 tmpfs에 소스를 복사해 해결했습니다.

## 2. 앱 빌드와 BAR 생성

| 용도 | 명령 | 결과 |
| --- | --- | --- |
| 실기기 ARMv7 | `npm run package` | `build/hello-cascades/HelloCascades-unsigned.bar` |
| 공식 x86 시뮬레이터 | `npm run package:simulator` | `build/hello-cascades-simulator/HelloCascades-simulator-unsigned.bar` |
| ARM 결과 검증 | `npm run verify` | ELF·QNX 로더·BAR 자산 확인 |
| x86 결과 검증 | `npm run verify:simulator` | 같은 항목을 x86 대상으로 확인 |

소스는 [examples/hello-cascades](examples/hello-cascades/)입니다. C++ 객체와 QML 버튼을 연결한 시작 예제이며 BBTube를 이식한 앱이 아닙니다. 생성되는 BAR는 미서명 개발 패키지입니다. 실기기에서는 OS 버전, 개발 모드, 인증·디버그 토큰 등 설치 조건을 별도로 확인해야 합니다.

## 3. Passport를 QEMU 자체 창으로 실행

```bash
./start_emulator_bb10.sh
```

QEMU GTK 창을 열고 Passport 1440×1440 프로필을 자동 선택합니다. 다른 폴더에서도 스크립트의 전체 경로로 실행할 수 있습니다. Ctrl+C 또는 QEMU 창 닫기로 종료합니다. 중복 실행은 기존 VM을 재부팅하지 않고 거부합니다. 실행 로그는 `emulator/state/vmvga-gtk-passport/start.log`입니다.

실행 전 준비 상태만 확인하려면 `./start_emulator_bb10.sh --check`, 도움말은 `--help`를 사용합니다. 빌드·다운로드·패키지 설치는 자동으로 수행하지 않습니다.

아래 기존 명령을 직접 사용하면 메뉴는 수동으로 선택합니다.

```bash
npm run simulator:passport:gui
```

부팅 중 Enter로 기기 메뉴를 열고 다음 항목을 선택합니다.

```text
4) BlackBerry 10 Keyboard [1440x1440]
```

기본 프로필로 이미 넘어갔다면 다른 터미널에서 다음 순서로 선택합니다. `menu`는 VM을 재부팅해 메뉴를 열고 일시 정지하므로 실행 중 앱 상태가 초기화됩니다.

```bash
node tools/simulator.mjs menu --state emulator/state/vmvga-gtk-passport
node tools/simulator.mjs resume --state emulator/state/vmvga-gtk-passport
node tools/simulator.mjs key 4 --state emulator/state/vmvga-gtk-passport
node tools/simulator.mjs key ret --state emulator/state/vmvga-gtk-passport
```

초기 서비스 준비에는 수 분이 걸릴 수 있습니다. `status`의 running은 QEMU 실행 상태이지 BB10 전체 서비스가 준비됐다는 뜻은 아닙니다.

| 해상도·배율 | 값 |
| --- | --- |
| 내부 앱 영역 | 1440×1440 |
| 내부 전체 영상 | 1536×1560: 테두리·시뮬레이터 상태줄 포함 |
| 게스트 자체 배율 | 100% |
| GTK 표시 배율 | 50% |
| 화면에 보이는 앱 영역 | 720×720 |
| 화면에 보이는 전체 영상 | 768×780: GTK 메뉴 높이는 별도 |

이는 실제 Passport ARM 하드웨어가 아니라 x86 개발 시뮬레이터의 Passport 화면 프로필입니다.

## 4. 상태·캡처·종료

```bash
npm run simulator:passport:status
npm run simulator:passport:screenshot
npm run simulator:passport:stop
```

동등한 직접 명령은 다음과 같습니다.

```bash
node tools/simulator.mjs status --state emulator/state/vmvga-gtk-passport
node tools/simulator.mjs display --state emulator/state/vmvga-gtk-passport
node tools/simulator.mjs screenshot --state emulator/state/vmvga-gtk-passport
node tools/simulator.mjs stop --state emulator/state/vmvga-gtk-passport
```

스크린샷은 `emulator/state/vmvga-gtk-passport/screen.ppm`이며 GTK에서 축소하기 전의 내부 프레임버퍼 크기입니다. `display`로 GTK `scale=0.5`, VNC 비활성, KVM 활성 여부를 확인할 수 있습니다.

기존 `npm run simulator:status/stop/screenshot` 명령의 기본 대상은 비교용 stock QEMU입니다. 최신 Passport에는 위 전용 명령이나 명시적인 `--state`를 사용합니다.

## 5. 앱 배포

게스트 서비스가 준비된 뒤 새 터미널에서 실행합니다.

```bash
BB10_DEVICE_HOST=127.0.0.1:4443 npm run deploy:simulator
```

기본 프로필에서는 전체 BAR 전송, 설치·실행, 버튼 Count 0→1을 확인했습니다. 최신 GTK Passport 프로필에서는 홈 화면·표시 배율을 확인했으며 같은 앱 배포를 재검증한 것은 아닙니다. 초기화 중 인증 CGI가 응답을 닫거나 인증 오류가 발생한 기록이 있습니다. QConn 동기화 최적화 연결 실패 뒤에도 전체 BAR 전송으로 성공한 사례가 있으므로 해당 경고만으로 설치 실패를 단정하지 않습니다.

실기기 주소·비밀번호는 [기기 안내](docs/development/DEVICES.ko.md)를 따릅니다. 비밀번호·키·토큰을 문서나 저장소에 기록하지 않습니다.

## 6. 비교용 VNC 경로

```bash
npm run simulator:passport
```

이전 USER 50% 설정 복사본을 사용하는 비교 경로입니다. 로컬 VNC 주소는 `127.0.0.1:5912`이며 RDP가 아닙니다. 준비된 Remmina 프로필은 `emulator/evidence/passport-live.remmina`입니다. 최신 GTK 경로와 컨테이너 이름·포트를 공유하므로 동시에 실행하지 않습니다.

## 7. 사운드 진단

기본 실행은 사운드카드를 추가하지 않습니다. 다음은 ES1370·PulseAudio 진단 옵션입니다.

```bash
BB10_AUDIO=es1370 BB10_TRACE_AUDIO=1 npm run simulator:passport:gui
```

BB10의 `audiopci` 드라이버는 ES1370 PCI ID를 인식하지만 필요한 `deva-mixer-ak4531.so`가 현재 이미지에 없습니다. 호스트 스트림 연결은 확인했으며 게스트 PCM 재생 성공은 확인하지 못했습니다. 실험 믹서는 기본 경로에 설치하지 않았습니다. [사운드 비교](docs/emulator/NATIVE-QEMU.ko.md#사운드-조사-결과)를 참고하세요.

## 8. 기존 환경의 재빌드와 자료 복구

| 작업 | 명령 | 조건 |
| --- | --- | --- |
| SDK 이미지 준비 | `npm run setup:sdk` | 이미지 저장소 접근 필요 |
| 원본 앱 참조 준비 | `npm run setup:references` | 고정 커밋을 사용 |
| 공식 VM 추출 | `npm run setup:simulator` | 보존 설치 파일 다운로드 또는 캐시 필요 |
| GTK QEMU 재빌드 | `npm run setup:simulator-gui` | 기존 VMVGA 런타임 이미지 및 빌드 의존성 다운로드 필요 |
| 참조 정적 검사 | `npm run audit:references` | 앱 참조 checkout 필요 |

현재 실행에는 `emulator/images`, `emulator/lib/dxvk`, Docker 이미지, `emulator/evidence/guest/passport-zoom50.raw`·`passport-zoom100.raw` 및 해당 QCOW2가 필요합니다. 일부 USER 설정 작성 도구는 **이 분석 시점 복사본에만 맞춘 실험 도구**입니다. 일반적인 임의 이미지 변환기나 완전히 새로운 호스트의 일괄 설치기라고 해석하지 않습니다.

## 9. 재분류 전 경로가 로그에 남아 있을 때

분석 증거 JSON·로그·과거 manifest는 당시 내용을 보존했습니다. 예전 `build/compat/...`, `sdk/simulator/...` 같은 경로는 [폴더 변경표](docs/LAYOUT.ko.md) 또는 `emulator/evidence/layout-migration-20261105/path-map.json`으로 현재 위치를 찾습니다. 문서·현재 설정·실행 스크립트는 새 경로를 사용합니다.
