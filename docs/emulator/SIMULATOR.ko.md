# QEMU 실험과 Passport 펌웨어의 차이

현재 작업의 두 대상은 서로 다릅니다.

| 경로 | 실행 이미지 | 현재 판단 |
| --- | --- | --- |
| Passport 하드웨어 에뮬레이션 | 실제 Passport용 ARM BB10 펌웨어 | 현재 설치된 QEMU에 해당 보드가 없어 준비된 실행 경로가 없음 |
| BB10 앱 개발 시뮬레이터 | BlackBerry의 x86 시뮬레이터 이미지 | VMVGA 3D 변형에서 홈 화면 확인, Passport 화면·배포 호환성은 보완 필요 |

**추가 조사에서 VMVGA + DXVK + 소프트웨어 Vulkan으로 BB10 홈 화면을 표시했습니다.** 재실행 명령과 기기별 결과는 [COMPATIBILITY.ko.md](COMPATIBILITY.ko.md)에 있습니다. 아래 QEMU 6.2 기록은 이전 비교 시험입니다.

## 실제 실행 결과: 2026-11-05

이미지 다운로드, 게시된 SHA-1 대조, VM 디스크 추출, QEMU 부팅까지 실행했습니다. 이미지 SHA-256은 `c00019a76add3ab9ab8065f4d30da77669d6620b906ea9b319ccd0605a41d78d`입니다.

| 시험 | 확인 결과 |
| --- | --- |
| QEMU 6.2 / KVM / 기본 All-Touch 프로필 | GUI 미표시, VGA 마지막 문구 `START SERVICE: screen` |
| QEMU 6.2 / KVM / 안전 모드 Keyboard 1440×1440 | 같은 VGA 문구, GUI 미표시 |
| QEMU 6.2 / TCG / 기본 프로필 | 같은 VGA 문구, GUI 미표시 |
| QEMU 6.2 / TCG / 안전 모드 Keyboard 1440×1440 | 같은 VGA 문구, GUI 미표시 |
| x86 GUI 예제 앱 | 후속 VMVGA + PCnet 수정 시험에서 설치·실행·버튼 동작 확인 |

부팅 메뉴의 일반·안전 모드 모두 `BlackBerry 10 Keyboard [1440x1440]` 항목이 존재합니다. 메뉴 선택까지 확인했지만 실제 1440×1440 GUI 표시에는 도달하지 못했습니다. 화면 캡처는 `emulator/state/stock/boot-menu.png`, `boot-safe-menu.png`, `passport-safe-screen.png`, `tcg-passport-safe-screen.png`에 보관했습니다. 상세 실행 기록은 `runtime-report.json`에 있습니다.

이는 **QEMU 6.2와 이 이미지의 조합에서 GUI가 표시되지 않았다는 결과**입니다. 이후 스크립트 분석으로 해당 문구 다음에 콘솔이 COM1로 전환되는 것을 확인했으므로 정확한 중단 함수는 확정할 수 없습니다. 또한 TCG도 TSS I/O 권한을 검사하므로 TCG 결과만으로 backdoor 권한 문제를 배제할 수 없습니다. 호스트 `enable_vmware_backdoor=N` 옵션은 변경하지 않았습니다.

이 QEMU 6.2 비교 시험 VM은 종료했습니다. VMVGA 경로는 별도 실행 도구와 overlay를 사용합니다. GUI 개발용 전체 검증은 아직 완료되지 않았으며, 실제 Passport ARM 펌웨어는 실행하지 않았습니다.

## 실제 Passport 펌웨어

`qemu-system-arm -machine help`로 이 호스트의 QEMU 6.2 보드 목록을 확인했으며 Passport 보드는 없습니다. 기록은 `emulator/state/stock/qemu-arm-machines.txt`와 `host-check.json`에 있습니다.

QEMU의 [ARM 보드 선택 문서](https://www.qemu.org/docs/master/system/target-arm.html)는 특정 하드웨어용 펌웨어가 다른 보드에서 일반적으로 부팅되지 않으며, 해당 보드의 구현 여부를 먼저 확인하도록 설명합니다. [virt 보드](https://www.qemu.org/docs/master/system/arm/virt.html)는 실제 Passport 하드웨어를 모델링한 장치가 아닙니다.

따라서 펌웨어 파일을 디스크 이미지로 변환하거나 CPU 종류만 맞춰서는 Passport 실행 환경을 만들 수 없습니다. CPU 외에도 메모리 맵, 부팅 초기화, 인터럽트·타이머·저장장치·그래픽·입력 등 OS가 기대하는 기기 인터페이스를 구현하거나, OS를 QEMU 지원 보드에 맞게 이식해야 합니다. 실제로 어떤 범위가 필요한지는 펌웨어 분석 없이는 단정할 수 없습니다.

`qemu-arm`으로 앱 바이너리만 호스트 Linux에서 실행하는 방식도 BB10 실행 환경을 제공하지 않습니다. QEMU의 [user-mode 지원 OS](https://www.qemu.org/docs/master/user/main.html)는 Linux/BSD이며 BB10의 QNX 시스템 호출과 GUI 서비스를 대신하지 않습니다.

실제 Passport ARM 펌웨어를 부팅하는 일은 별도의 하드웨어 에뮬레이터 개발·펌웨어 분석 과제입니다. 이번 시뮬레이터 준비에서 실기기 펌웨어를 수정하거나 플래시하지 않습니다.

## 공식 x86 시뮬레이터를 이용하는 경로

보존된 Linux용 BB10 시뮬레이터 10.3.1.2558을 대상으로 합니다. 파일 길이와 Internet Archive에 기록된 SHA-1을 `emulator/config/simulator.lock.json`에 고정했습니다. 보존 출처의 일관성 확인이며 공식 서명 검증을 뜻하지 않습니다.

시뮬레이터는 VMware용 가상 머신입니다. 확인한 VMX에는 IDE 디스크, RAM 2048MB, VMware SVGA와 `mks.enable3d = TRUE` 설정이 있습니다. QEMU에서는 이 장치들을 최대한 맞춰 부팅을 실험합니다. QEMU 6.2의 `vmware-svga` 구현은 3D capability를 제공하지 않으므로, 부팅이 되더라도 GUI까지 정상 실행된다고 가정할 수 없습니다. 이 한계는 확인한 [QEMU 6.2 원본](https://github.com/qemu/qemu/blob/v6.2.0/hw/display/vmware_vga.c)의 capability 반환 코드에 근거합니다.

이 경로는 **x86 BB10 시뮬레이터**입니다. 화면 크기를 Passport에 맞춰 설정하더라도 실제 Passport 펌웨어·GPU·무선통신·키보드 하드웨어가 재현되는 것은 아닙니다. VMVGA의 1440×1440 프로필은 기본 66% 확대에서 왜곡이 있었고, 별도 복사본에서 50%로 바꿔 정상 형태의 홈 화면을 확인했습니다.

### 이미지 준비

```bash
npm run setup:simulator
npm run doctor:simulator
```

`setup:simulator`는 기존 호스트 Node를 통해 Python 표준 라이브러리와 curl을 호출합니다. 구버전 설치 프로그램을 실행하지 않고, 길이/SHA-1을 검증한 설치 파일 안의 ZIP에서 VM 파일만 추출합니다. 다운로드는 최대 8개의 연결로 1MiB 구간을 병렬 처리하고 완료한 구간은 재사용합니다. 원본 파일과 구간 캐시는 `emulator/downloads/`, 추출한 읽기 전용 VM 디스크는 `emulator/images/10.3.1.2558/`에 보관합니다.

기본 VM 디스크를 바꾸지 않도록 실행 시 `emulator/state/stock/BB10.qcow2` 쓰기 overlay를 만듭니다. 여러 GB의 여유 공간이 필요합니다.

### 시뮬레이터용 GUI 앱 빌드

```bash
npm run package:simulator
npm run verify:simulator
```

결과물은 `build/hello-cascades-simulator/HelloCascades-simulator-unsigned.bar`입니다. x86 ELF, QNX 로더, BAR 아키텍처·자산을 검증했습니다. 실기기용 기존 ARM BAR는 시뮬레이터에서 직접 사용하지 않습니다.

### QEMU 실행과 점검

```bash
npm run simulator:start -- --dry-run
npm run simulator:start
npm run simulator:status
npm run simulator:screenshot
npm run simulator:stop
```

이 호스트에는 KVM이 있으며 샌드박스 밖에서 접근 가능합니다. 접근 가능한 경우 KVM을 사용하고, 그렇지 않으면 TCG를 사용합니다. TCG를 명시하려면 `npm run simulator:start -- --tcg`로 실행합니다.

OS 이미지를 연결하지 않은 짧은 사전 점검에서 KVM, VMware SVGA 128MB, QMP 초기화 및 정상 종료를 확인했습니다. 결과는 `emulator/state/stock/kvm-smoke.json`입니다. 이는 BB10 부팅 성공을 의미하지 않습니다.

화면은 로컬 VNC `127.0.0.1:5910`에서 확인할 수 있습니다. QMP 스크린샷은 `emulator/state/stock/screen.ppm`, 시리얼 로그는 `serial.log`에 생성합니다. 부팅 메뉴에 키 입력이 필요하면 예를 들어 `node tools/simulator.mjs key ret`를 사용할 수 있습니다.

설치된 Tesseract를 사용하는 선택적 진단 명령 `node tools/simulator.mjs menu`는 VM을 재부팅하고 화면에서 기기 선택 프롬프트를 감지한 뒤 Enter를 보내 메뉴를 열고 일시 정지합니다. `node tools/simulator.mjs resume`으로 재개한 후 `key 6`, `key ret`로 안전 모드 메뉴를 열고, `key 4`, `key ret`로 1440×1440 키보드 프로필을 선택할 수 있습니다. 메뉴 입력 후 화면이 갱신될 시간을 둡니다. 이 선택 절차도 GUI 초기화 문제를 해결하지는 못했습니다.

네트워크는 외부 접근을 제한한 QEMU user network입니다. 로컬 포트 2222→guest SSH 22, 2323→Telnet 23, 2443→HTTPS 443을 전달합니다. 포트 전달은 guest 서비스의 동작이나 앱 설치 성공을 보장하지 않습니다. 실제 배포 연결은 guest 부팅 후 확인합니다.

부팅 후 배포 API가 준비되면 `npm run deploy:simulator`로 x86 예제를 설치·실행할 수 있습니다. 기본 주소는 `127.0.0.1:2443`이며 필요하면 `BB10_DEVICE_HOST`로 변경합니다. 시뮬레이터에서는 비밀번호를 생략할 수 있게 했으며, 해당 guest 설정에 따라 인증이 필요하면 `BB10_DEVICE_PASSWORD`를 지정합니다. 이 명령의 실제 성공 여부는 런타임 검증 기록을 확인합니다.

QEMU 프로세스 시작, QNX 부팅, BB10 홈 화면 표시, 앱 설치, 버튼 동작은 각각 확인해야 합니다. `simulator:status`의 running은 QEMU 프로세스 상태이며 BB10 GUI 실행 성공 판정이 아닙니다.

공식 시뮬레이터의 입력·Controller·기기 설정은 [BlackBerry Simulator User Guide](https://developer.blackberry.com/devzone/files/develop/simulator/BB10_Device_Simulator_UG.pdf)를 참고합니다. QEMU에서 Controller의 모든 기능이 동작한다고 가정하지 않습니다.
