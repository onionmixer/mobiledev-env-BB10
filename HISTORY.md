# 작업 이력과 판단 정정

작업일: **2026-11-05**. 대상은 Z10·Passport용 앱 개발 기반과 Linux의 BB10 개발 시뮬레이터입니다. 단계별 정확한 시각이 없는 부분에 임의의 시각을 붙이지 않았습니다. 원시 JSON·로그에 있는 UTC 시각과 호스트의 한국 표준시 표시는 서로 다를 수 있습니다.

이 문서에서 **관찰**은 실제 실행·파일·코드에서 확인한 내용, **추정**은 근거가 있으나 대상 환경에서 직접 측정하지 않은 내용, **미검증**은 아직 성공을 입증하지 못한 범위입니다. 최신 사용법은 [HOWROUSE](HOWROUSE.md)에 있고, 아래 과거 시험은 당시의 구현과 프로필에만 적용됩니다.

## 1. 최초 요구와 기술 범위

사용자는 `bb10-native-tools`, `bb10-webworks-framework`, `bbtube`, `balika011.hu/blackberry/`를 분석하고 Momentics 없이 개발할 기반을 요청했습니다. 중복으로 제시된 BBTube URL은 하나로 취급했습니다. 이후 호스트 Node를 그대로 사용하고 Z10·Passport를 대상으로 하도록 범위가 구체화됐습니다.

참조 소스는 [앱 참조 고정 정보](config/references.lock.json)에 기록했습니다. 네이티브 시작 경로로 C++·Qt 4.8·Cascades·QML을 선택했습니다. WebWorks에 대한 현재 Node 정적 API 검사에서는 제거된 `path.exists`, `path.existsSync`, `util.puts` 호출 지점 60곳을 찾았습니다.

**한계:** 정적 검사 결과를 WebWorks 전체 빌드·동작 검증으로 해석하지 않습니다. BBTube 소스의 구조를 참고했지만 BBTube 앱이나 YouTube 재생을 이식·검증한 것이 아닙니다. 새 예제는 독립적인 버튼 카운터 앱입니다.

## 2. CLI SDK와 호스트 실행 문제

호스트 Node `20.20.2`를 유지했습니다. 보존된 `accupara/bbndk` 이미지를 digest로 고정하고 IDE·기본 이미지 서비스를 시작하지 않은 채 qmake·qcc·packager만 호출했습니다. SDK host 도구는 `10.3.1.12`, API/sysroot는 `10.3.1.995`, Qt는 `4.8.6`입니다. [SDK 고정 정보](config/sdk.lock.json)에 근거가 있습니다.

호스트 XFS의 inode 번호가 32비트 범위를 넘는 환경에서 오래된 32비트 qmake/qcc의 파일 조회·target 탐색이 실패했습니다. 소스를 컨테이너 tmpfs에 복사해 빌드하는 방식으로 ARMv7와 x86 ELF 및 BAR를 생성했습니다.

**구분:** 이 파일 조회 문제와, 샌드박스가 하위 프로세스·32비트 실행을 SIGSYS/EPERM으로 막은 문제는 다릅니다. 후자는 허용된 호스트 실행에서 재검사했습니다. 이를 SDK 자체 고장이나 모든 Linux 환경의 제약으로 일반화하지 않았습니다.

ARM·x86 패키징 성공은 확인했지만 실제 Z10·Passport 설치·실행을 뜻하지 않습니다. 실기기 개발 모드·인증·서명·디버그 토큰 및 OS 버전 조건은 별도입니다.

## 3. 실제 Passport 펌웨어와 공식 x86 시뮬레이터의 분리

사용자는 Linux 에뮬레이터와 QEMU, 실제 Passport 펌웨어 실행 가능성을 물었습니다. 호스트 QEMU 6.2의 ARM 보드 목록을 확인했으며 Passport 보드는 없었습니다. 임의의 ARM CPU나 `virt` 보드에 실제 Passport 펌웨어를 연결하는 것만으로 실행할 수 있다고 판단하지 않았습니다.

실제 시험에는 **공식 BB10 x86 개발 시뮬레이터 10.3.1.2558**을 사용했습니다. 이는 ARM Passport 펌웨어가 아닙니다. Passport 화면 프로필이 존재해도 Qualcomm 보드·GPU·무선통신·실물 키보드 전체를 에뮬레이션했다는 뜻이 아닙니다. `qemu-x86` 사용자 모드 실행도 QNX 시스템 호출과 BB10 GUI 서비스를 대신하지 않습니다.

**미수행:** 실제 Passport ARM 펌웨어 부팅, 실기기 플래시, 실기기 하드웨어 에뮬레이터 구현.

## 4. 보존 이미지 확보와 추출

Linux 설치 파일을 보존 저장소에서 확보했습니다. 파일 길이 `1,166,574,715`바이트와 게시된 SHA-1 `b99bc314e9b9840942057f508e87054874ad5ea6`을 대조했습니다. 직접 계산한 SHA-256은 다음과 같습니다.

```text
c00019a76add3ab9ab8065f4d30da77669d6620b906ea9b319ccd0605a41d78d
```

구형 설치 프로그램은 실행하지 않고 내부 VM ZIP에서 VMDK·VMX 등을 추출했습니다. InstallAnywhere ZIP의 비표준 extra field와 대용량 중첩 ZIP을 처리하는 추출 도구를 작성했습니다. 원본 VMDK는 읽기 전용으로 보존하고 실제 쓰기는 QCOW2 overlay에 했습니다.

**한계:** 보존 출처의 길이·해시 일치와 공식 배포자의 서명 검증은 다릅니다. [시뮬레이터 고정 정보](emulator/config/simulator.lock.json)에 출처와 검증 대상을 기록했습니다.

## 5. 배포판 QEMU 6.2 시험과 최초 해석의 정정

KVM·TCG에서 기본 All-Touch 및 안전 모드 Keyboard 1440×1440을 비교했습니다. QNX와 기기 메뉴는 확인했지만 GUI는 표시되지 않았고 VGA에 `START SERVICE: screen` 문구가 남았습니다.

초기에 이를 “screen 서비스에서 멈춤”으로 표현했습니다. **이 표현은 정확한 중단 위치를 입증하지 못해 정정했습니다.** 추후 실제 startup 스크립트를 읽어 보니 `SERVICE_screen`은 screen 실행 전에 COM1 드라이버를 시작하고 콘솔을 `/dev/ser1`로 전환합니다. 따라서 마지막 VGA 문구만으로 screen 함수 자체가 막혔다고 단정할 수 없습니다.

현재 유지하는 관찰은 “해당 QEMU 6.2 조합에서 GUI 미표시, 마지막 VGA 문구 확인”입니다. 모든 QEMU 버전·수정 구현에서 불가능하다는 결론으로 해석하지 않습니다.

근거: [QEMU 6.2 기록](emulator/state/stock/runtime-report.json), [추출·부팅 스크립트 설명](emulator/research/guest/README.md). stock 보고서의 표현은 추가 조사 당시 이미 정정했으며 이번 재분류 때 원시 보고서 내용을 다시 쓰지 않았습니다.

## 6. 파일시스템·부팅 구성 조사

원본에서 만든 복사본을 읽어 QNX6 boot/USER, RCFS `/base`, UCL 압축 IFS를 조사했습니다. 커널 파일시스템으로 마운트하지 않고 사용자 공간의 제한된 파서로 파일을 추출했습니다. RCFS 구조는 원본 소스와 REA/Ghidra의 `fs-rcfs.so` 분석을 대조했습니다.

`rimh` 래퍼가 있다는 이유만으로 전체 내용을 암호화됐다고 판단하지 않았습니다. 해당 이미지에서는 RCFS 구조와 LZO 블록을 해석해 startup·그래픽·오디오 파일을 읽었습니다. IFS는 독립적인 체크섬과 추출 manifest를 남겼습니다.

안전 모드는 software 경로를 선택하지만 디스플레이는 여전히 `libHwWFDvmware.so`를 사용했습니다. 따라서 안전 모드가 VMware 화면 호환성 요구를 없앤다고 가정하지 않았습니다. inspect한 스크립트에서는 임의의 writable USER 시작 훅을 찾지 못했지만 모든 가능한 QNX override 방법이 없다고 단정하지 않았습니다.

증거: [RCFS REA bundle](emulator/evidence/rcfs-evidence.json), [guest_info bundle](emulator/evidence/guest-info-evidence.json), [추출 도구·범위](emulator/research/guest/README.md). 디컴파일 결과는 원본 소스 복원이 아닌 분석 자료이며, 게스트 바이너리를 호스트 Linux에서 실행한 것이 아닙니다.

## 7. backdoor·TCG·시리얼 가설의 범위

호스트 KVM의 `enable_vmware_backdoor=N`을 확인했지만 값을 바꾸지 않았습니다. “TCG에서도 같은 결과이므로 backdoor 권한 문제를 제외할 수 있다”는 식으로 판단해서는 안 됩니다. TCG도 IOPL/TSS I/O 권한을 검사합니다.

VMVGA 배포 실행 파일의 qemu-windows TSS 패치도 조사했습니다. 실제 패치는 64비트 long mode 및 특정 Windows TSS 구조를 요구했습니다. 로그의 `ready`는 준비 상태일 뿐 패치 적용을 뜻하지 않았고, 이번 32비트 BB10 로그에는 활성화·수정 증거가 없었습니다. GUI 성공을 이 자동 TSS 패치 효과로 설명하지 않았습니다.

시리얼 파일 backend의 carrier 대기, XON/XOFF, IRQ 문제도 후보로 조사했으나 파일 backend 때문에 반드시 막힌다는 근거는 확보하지 못했습니다. 단일 XON 바이트로 screen 실행 여부나 입력 대기를 단정하지 않았습니다.

근거: [시리얼·TSS·정확한 fork 조사](emulator/evidence/source-report/serial-backend-and-vmport.md). 최종적으로 stock QEMU 6.2의 최초 무출력 원인 전체를 하나의 함수·옵션으로 확정한 것은 아닙니다.

## 8. VMVGA로 그래픽 경로 확장

기본 QEMU의 제한적인 `vmware-svga`와 별도로 `qemus/qemu-vmvga` v1.03을 조사했습니다. 소스 커밋은 `073c4dc64e49dd082c70f249dd883cba7ea93f43`입니다. 보존 실행 파일의 glibc·virglrenderer 요구 때문에 Debian 기반 격리 런타임을 만들었습니다. 호스트 Node·그래픽 드라이버·커널 옵션은 바꾸지 않았습니다.

DXVK native 2.7.1과 Mesa llvmpipe 소프트웨어 Vulkan을 준비했습니다. Vulkan 버전·확장 열거는 사전 조건 확인일 뿐 GUI 성공 증거로 취급하지 않았습니다. 실제 게스트의 SVGA3D 명령 처리와 실제 화면을 후속 확인했습니다.

| 실제 시험 | 관찰 |
| --- | --- |
| VMVGA `3d=off` | 잠금 화면까지 진행했으나 심한 비틀림 |
| VMVGA `3d=on,vgpu=9` + DXVK | 기본 프로필의 정상 형태 홈 화면 |
| 같은 3D 경로, Passport 기본 66% | 잠금·제스처 반응이 있으나 줄 간격·색상 왜곡 |

이 결과를 단순한 stock QEMU 버전 업그레이드로 재현된다고 주장하지 않습니다. 정확한 구현·버전·호스트 라이브러리 조합을 구분했습니다.

## 9. PCnet: 초기 가설에서 실제 원인으로

처음에는 IP 획득 실패와 짧은 추적 구간에서 게스트 패킷·레지스터 접근이 없었습니다. 이를 곧바로 MAC 제한, PCI 탐색 실패 또는 IRQ 고장으로 확정하지 않았습니다. 더 기다린 뒤 PROM 읽기와 초기화 접근이 실제 기록됐습니다. **초기 추적 부재는 그 관찰 시간 구간에 한정합니다.**

게스트 드라이버 코드에서 VMware MAC/OUI 필수 조건이나 PCI revision 거부 조건은 발견하지 못했습니다. `if_up -p`는 IP가 아니라 인터페이스 존재 여부를 기다렸습니다. 정확한 QEMU fork에서도 MMIO·I/O는 같은 PCnet 추적 함수를 사용하므로 MMIO라서 로그가 없다는 해석도 제외했습니다.

후속 추적에서 직접적인 불일치를 확인했습니다. 게스트는 DWORD 접근 모드(DWIO)를 켠 다음 software reset을 읽고, 다시 DWIO를 켜지 않은 채 DWORD 설정을 썼습니다. QEMU는 reset에서 DWIO를 지우므로 SWSTYLE 설정이 무시되고 CSR1의 첫 쓰기는 모드 재활성화에만 사용돼 실제 값이 버려졌습니다.

예를 들어 의도한 초기화 주소 `0x78f9ec00` 대신 실제 `0x78f90000`에서 잘못된 형식·큐 크기로 초기화했습니다. 이후 관찰된 INTA/IDON 처리 때문에 이 현상을 단순한 “IRQ가 전혀 전달되지 않음”으로 설명하지 않았습니다.

근거: [추적과 소스 대조](emulator/evidence/source-report/pcnet-dwio-reset.md), [게스트 PCnet REA](emulator/evidence/guest/network/pcnet-evidence.json), [이전 추적](emulator/state/vmvga-3d/pcnet-baseline.log).

## 10. PCnet 호환성 우회와 DHCP 확인

원본을 보존한 별도 QEMU 실행 파일에서 `pcnet_s_reset()`의 DWIO 해제만 막았습니다. ELF 파일 오프셋 `0x63fa50`의 AND 명령 즉시값을 바꾸는 한 바이트 수정으로 시험했으며 hard reset 동작은 유지했습니다. REA/Ghidra 분석의 주소에는 image-base 차이가 있어 파일 오프셋과 혼동하지 않았습니다.

수정 후 `ss32=1`, 수신 큐 64개·송신 큐 128개가 확인됐고 DHCP 교환과 `10.0.2.15` 획득, HTTPS 접속이 동작했습니다. 하단의 `Getting IP...` 표시는 이후에도 남아 있어 실제 네트워크 판정 기준으로 쓰지 않았습니다.

**중요한 범위:** [AMD 명세](https://www.amd.com/content/dam/amd/en/documents/archived-tech-docs/datasheets/19436.pdf)는 software reset에서 DWIO를 지우도록 규정합니다. 따라서 이것은 일반적인 AMD PCnet/QEMU 버그 수정이라고 주장할 수 없는 **BB10 호환성 우회**입니다. 실제 VMware가 이 비트를 보존하는지는 측정하지 않았습니다. 관찰한 것은 BB10 드라이버의 접근 순서와 이 우회 후의 결과입니다.

원본 실행 파일 SHA-256은 `ce36d097fd0954ba64462decd0b6ffc2d5448dcb843b76f3c535bfa790c21599`, 별도 PCnet 시험본은 `a3000be09118c82075ecd381d9547a80065481d080a7f67803ba9560b70425dd`입니다. 후속 GTK 빌드에는 같은 의미의 수정을 소스로 적용했습니다.

근거: [수정 도구](emulator/research/guest/patch_pcnet_dwio.py), [소스 diff](emulator/research/guest/pcnet-preserve-dwio-experiment.patch), [QEMU 분석](emulator/evidence/qemu-pcnet-evidence.json), [수정 후 추적](emulator/state/vmvga-3d/pcnet-patched.log), [패킷](emulator/state/vmvga-3d/network-patched.pcap).

## 11. 앱 배포와 실제 버튼 동작

서비스 초기화 도중에는 HTTPS 인증 CGI가 응답을 닫았고 SDK 배포가 실패했습니다. 초기화 뒤 같은 배포 명령으로 미서명 x86 개발 BAR의 설치·실행이 성공했습니다. QConn 동기화 최적화 연결은 실패했지만 전체 BAR 전송은 성공했습니다.

SDK의 `result::success`와 실행 PID만으로 GUI 이벤트까지 검증했다고 판단하지 않았습니다. 실제 Cascades 화면의 `button count: 0`을 확인한 뒤 버튼을 눌러 `1`로 바뀐 화면을 보존했습니다.

**이 성공의 대상은 기본 프로필입니다.** 실제 ARM 기기, 모든 Passport 복사본, 모든 최신 실행 경로에서 같은 설치·버튼 검증을 다시 완료했다는 뜻은 아닙니다.

근거: [배포 로그](emulator/state/vmvga-3d/deploy-hello-ready.log), [Count 0](emulator/state/vmvga-3d/hello-cascades.png), [Count 1](emulator/state/vmvga-3d/hello-cascades-count.png).

## 12. Passport의 첫 화면 보정: 게스트 zoom 50%

기본 66% 확대에서는 전체 출력 폭이 1013이 됐고 색상 줄무늬·비틀림이 있었습니다. 종료한 VM overlay를 RAW로 복사하고, 별도 복사본의 `mesa` PPS에 Passport `0.50` 설정을 추가했습니다. 기존 할당 블록 안의 설정 89바이트와 inode 크기 필드 8바이트만 썼으며 공식 이미지·원래 RAW는 보존했습니다.

50% USER 복사본은 전체 768×780 출력으로 정상 형태 홈 화면을 보였습니다. 이 비교로 확대 배율에 따른 우회는 확인했으나 정확한 renderer/stride 결함 전체를 입증한 것은 아닙니다.

이 복사본의 앱 재배포는 `peer not authenticated`로 실패했고 관찰 종료 시 초기화 기록도 `bbio` 이후 완료되지 않았습니다. 실패 원인을 zoom 변경 자체로 확정하지 않았으며 이 복사본의 앱 배포 성공을 기록하지 않았습니다.

근거: [50% 설정 manifest](emulator/evidence/guest/passport-zoom50-manifest.json), [홈 화면](emulator/state/vmvga-3d-zoom50/passport-home.png), [배포 실패 로그](emulator/state/vmvga-3d-zoom50/deploy-hello.log).

## 13. 캡처 표시와 실시간 화면의 구분

사용자 요청으로 실제 캡처들을 eog로 열었습니다. 이어 기본·Passport 홈 화면 캡처를 표시했고 사용자가 확인했습니다. eog로 이미지를 보는 것은 에뮬레이터 조작이나 실행 재검증이 아닙니다.

그 뒤 Passport VM을 켜고 Remmina로 실시간 화면을 열었습니다. 연결 프로필의 프로토콜은 **VNC**였으며 RDP가 아니었습니다. VNC 서버는 게스트 BB10의 원격 데스크톱이 아니라 **QEMU가 제공하는 화면·입력 통로**였습니다. 이후 사용자가 Remmina를 종료했습니다.

## 14. QEMU 자체 GTK 창 준비

사용자가 QEMU 자체 창을 요청했습니다. 기존 배포 실행 파일의 `-display help`에는 GTK·SDL이 없었고, qemu-windows Dockerfile도 두 기능을 끄고 있었습니다. 이를 QEMU나 BB10의 근본적인 직접 표시 불가능으로 해석하지 않았습니다.

고정한 QEMU Helios `6577af923eac07522b4a6879854f1469c48c5801`, VMVGA v1.03, qemu-windows `21b0444a253624cf087d809e90f1c2caba392cc4` 패치 및 PCnet 소스 우회로 GTK 빌드를 준비했습니다. 전체 식별자는 [QEMU GUI 고정 정보](emulator/config/qemu-gui.lock.json)에 있습니다.

재빌드에 필요한 보완을 기록했습니다.

- 오프라인 Python 준비에 wheel·setuptools와 vendored qemu.qmp wheel이 필요했습니다.
- Helios가 고정한 Vulkan-Headers 하위 모듈과, Meson wrap의 softfloat/testfloat `packagefiles`를 함께 준비해야 했습니다.
- 실행 이미지의 누락된 `libsndio.so.7`을 의존성 대조 후 보완했습니다.
- **GTK·SDL을 함께 링크한 첫 빌드는 실제 SDL이 먼저 로드돼 DXVK headless WSI 초기화가 실패했습니다.** GTK 전용으로 다시 빌드해 해결했습니다. 최종 빌드는 GTK·PulseAudio 활성, SDL 프런트엔드 비활성입니다.

컴파일 완료와 산출물 검증 단계도 구분했습니다. 빌드 스크립트 갱신과 겹쳐 후처리가 실패했던 실행은 최종 산출물로 채택하지 않았고, 실제 빌드 디렉터리의 실행 파일을 직접 검사해 올바른 파일을 실행 이미지에 반영했습니다. 최종 GUI 실행 파일 SHA-256은 `a703a90d7eb3cc0212cbc52a1a2e02f6fc2b482f5aecb187d1dc920f4935697b`입니다.

호스트 패키지를 설치·교체하지 않고 Docker 안에 빌드·실행 의존성을 두었습니다. X11 소켓과 해당 DISPLAY 인증 쿠키만 전달했고 `xhost` 접근 권한은 바꾸지 않았습니다.

## 15. 최종 배율: 내부 1440 유지, 호스트만 50%

사용자가 화면 표시만 절반이고 내부 해상도는 1440×1440이길 요청했습니다. 이전 게스트 zoom 50% 경로와 구분해, 별도 USER 복사본의 Passport zoom을 `1.00`으로 바꾸고 QEMU GTK의 `scale=0.5`, `zoom-to-fit=off`를 사용했습니다. 이 변경은 같은 길이의 PPS 값 변경이며 inode 크기는 바꾸지 않았습니다.

QMP 원본 캡처는 전체 **1536×1560**, 앱 clip 영역은 **1440×1440**입니다. GTK가 전체 영상을 **768×780**, 앱 영역을 **720×720**으로 보여줍니다. 검증한 GTK 클라이언트는 메뉴 26픽셀이 포함돼 768×806이었습니다. 전체 창을 정사각형으로 강제 변형한 것이 아닙니다.

QMP에서 `type: gtk`, `scale: 0.5`, VNC `enabled: false`, KVM `enabled: true`를 확인했습니다. 실제 QEMU 창에서 홈 화면이 보였고 사용자도 도달을 확인했습니다. 사용자 확인을 전체 BB10 서비스·앱 배포·사운드 성공으로 확대 해석하지 않았습니다.

근거: [표시 설정](emulator/state/vmvga-gtk-passport/display-options.json), [내부 홈 화면](emulator/state/vmvga-gtk-passport/internal-home.png), [QEMU 창](emulator/state/vmvga-gtk-passport/gtk-window.png), [당시 런타임 기록](emulator/state/vmvga-gtk-passport/runtime-report.json).

## 16. 사운드: 장치·드라이버·믹서·재생의 구분

사용자는 QEMU에 필요한 드라이버와 원본 VMware 구성을 함께 확인하도록 요청했습니다. 원본 VMX의 hardware version은 7이며 `sound.present=TRUE`, 자동 선택이었고 **`sound.virtualDev`는 없었습니다**. 실제 VMware 세션의 PCI inventory는 확보하지 못했습니다.

VMware 개발자는 관련 Workstation/Fusion 버전에서 해당 옵션이 없으면 ES1371을 사용한다고 설명했습니다. 이를 2015년 이미지에 적용한 것은 **출처에 근거한 추정**이며, 원본 VMware에서 실제 측정한 결과로 기록하지 않습니다.

실제 게스트 드라이버와 믹서 로딩 코드는 REA/Ghidra로 조사했습니다.

| 컨트롤러 | 게스트 코드·이미지에서 확인한 내용 |
| --- | --- |
| ES1371 계열 | `1274:1371`, `1274:5880`, `1102:8938`을 지원. `ac97` 믹서를 선택하고 해당 라이브러리가 존재 |
| QEMU ES1370 | `1274:5000`을 지원하지만 `ak4531` 믹서를 요구하며 이미지에 `deva-mixer-ak4531.so`가 없음 |
| QEMU Intel AC97 | `8086:2415`로, 고정된 BB10 `audiopci` 드라이버의 지원 PCI ID와 다름 |

따라서 “QNX가 ES1370을 전혀 지원하지 않는다”는 결론은 부정확합니다. 현재 이미지의 ES1370 믹서 구성 누락이 확인된 것입니다. 또한 AC97 믹서가 있다는 이유만으로 QEMU Intel AC97 카드가 VMware ES1371과 같다고 볼 수 없습니다.

GTK 실행에서 ES1370 PCI 카드와 호스트 PulseAudio 클라이언트·출력 스트림을 확인했습니다. 그러나 게스트 preferred PCM 장치 대기가 시간 초과했고, ES1370 추적에는 초기 형식 설정만 있으며 PCM 전송을 관찰하지 못했습니다. **실제 재생 성공은 미검증입니다.** 호스트 스트림이 열리거나 무음 파일이 생기는 것만으로 재생 성공을 판정하지 않습니다.

별도 AK4531 실험 플러그인을 x86으로 빌드했습니다. 실제 코덱 쓰기·볼륨·음소거 콜백의 호스트 테스트와 DDS 가져오기 심볼 검증은 통과했지만, 일부 DDS 헤더가 SDK에 없어 제한된 ABI 선언을 사용했습니다. **게스트에 로드·설치·재생하지 않았고 기본 실행에도 넣지 않았습니다.** QEMU ES1370의 아날로그 gain/mute 모델 한계도 별도로 기록했습니다.

근거: [사운드 구성·출처·실험 범위](emulator/research/audio/README.md), [게스트 오디오 분석](emulator/evidence/guest/audio/audiopci-evidence.json), [실행 진단](emulator/state/vmvga-gtk-passport/audio-check.json).

## 17. 폴더 재분류와 증거 보존

사용자가 `tools`·`docs`·`emulator` 중심 재분류와 루트 README·HOWROUSE·HISTORY를 요청했고 신중한 진행을 강조했습니다. 이어 사용자가 QEMU를 종료했다고 알려 주었으며 Docker에서도 해당 VM이 없는 것을 확인한 후 작업했습니다.

이동 전 계획·파일 식별 정보·문서/스크립트/설정·앱 검증 결과·다섯 overlay를 보존했습니다. 26개 경로를 이동하면서 **28,827개 파일의 device/inode·크기·수정 시각·모드·심볼릭 링크 대상을 대조**했습니다. 데이터 파일은 이름 변경으로 이동했고 이 대조에서 불일치가 없었습니다.

QCOW2 다섯 개의 절대 backing 경로는 `qemu-img rebase -u`로 새 위치에 맞췄습니다. 각 backing 데이터의 식별 정보가 이동 전과 동일함을 확인한 뒤 메타데이터만 변경했고, 다섯 이미지 모두 `qemu-img check`에 통과했습니다. **QCOW2 메타데이터 검사 통과는 게스트 QNX 파일시스템의 완전한 무결성 검사를 뜻하지 않습니다.**

당시 증거 JSON·로그·manifest 안의 예전 절대 경로와 실행 상태는 역사적 내용으로 보존했습니다. 예전 보고서의 `running` 또는 `stopped` 값은 그 보고서 시점의 값이며 현재 상태 판정에 사용하지 않습니다. 현재 실행 스크립트·설정·문서만 새 경로로 바꿨습니다. 준비 도구가 재실행될 때도 원래 evidence manifest를 덮어쓰지 않고 `emulator/state`에 현재 준비 기록을 씁니다.

보존 위치: [재분류 안내](docs/LAYOUT.ko.md), [이동표](emulator/evidence/layout-migration-20261105/path-map.json), [전환 journal](emulator/evidence/layout-migration-20261105/journal.json). 당시 문서·스크립트 원본은 같은 폴더의 `before/`, overlay 백업은 `overlay-backups/`입니다. 역사적 해석에는 이 백업과 원시 증거를 함께 사용할 수 있습니다.

재분류 후 SDK 점검, x86 예제 재빌드·패키징·검증, 기존 ARM BAR 검증, 참조 정적 검사가 통과했습니다. 별도 overlay와 Xvfb 가상 화면에서 Passport 홈 화면을 다시 확인했고, 내부 1536×1560·GTK 50%·VNC 비활성·KVM 활성을 검증했습니다. 이 검사는 앱 버튼·사운드 재생을 새로 검증한 것이 아닙니다.

검증용 VM은 종료했습니다. 원래 다섯 overlay의 해시는 backing 메타데이터 변경 직후와 같았으며, 별도 실행 검사가 원래 overlay를 바꾸지 않았음을 대조했습니다. 최종 수치와 로그는 [재분류 검증 보고서](emulator/evidence/layout-migration-20261105/verification.json)에 있습니다. 증거에 과거 `running`이 남아 있어도 완료 시점에는 BB10 VM이 모두 종료된 상태였습니다.

## 18. 앞으로도 유지해야 할 검증 경계

- 기본 프로필의 앱 설치·Count 검증, Passport 50% USER 시험, 최신 GTK 100% 내부 해상도 시험을 합쳐 하나의 모든 기능 성공으로 쓰지 않습니다.
- 공식 x86 시뮬레이터와 실제 Passport ARM 펌웨어·실기기 실행을 구분합니다.
- source commit·해시 고정은 보존 내용의 일관성을 위한 것이며 공식 배포자 인증이나 외부 apt 저장소까지의 완전한 재현성을 뜻하지 않습니다.
- PCM 재생, 전체 Controller·센서·오디오 입력·장시간 안정성·실기기 서명 및 설치는 성공이 확인되기 전까지 미검증으로 남깁니다.
- 현재 준비 스크립트와 분석 시점에 한정된 USER 수정 도구를 임의 이미지용 범용 설치기로 설명하지 않습니다.
- 다음 조사에서 원인이 바뀌면 이전 판단을 조용히 지우기보다 관찰·가설·정정 근거·적용 범위를 함께 남깁니다.

## 19. 루트 일괄 실행 스크립트

사용자 요청으로 실행 권한을 가진 [start_emulator_bb10.sh](start_emulator_bb10.sh)를 루트에 추가했습니다. 기존 GTK 실행 도구를 호출하고 QMP 준비를 확인한 뒤, 부팅 프롬프트를 실제 OCR로 감지해 Passport 항목 4를 선택합니다. 일정 시간을 무조건 기다렸다가 키를 보내는 방식은 사용하지 않았습니다.

스크립트 위치를 기준으로 경로를 계산하며 `--check`·`--help`를 제공합니다. 동일 프로필의 파일 잠금과 기존 컨테이너 확인으로 중복 실행을 거부합니다. 시작마다 Docker label에 실행 식별자를 넣어, 종료 처리 시 자신이 만든 컨테이너인지 확인한 뒤 정리합니다. 다운로드·SDK 설치·사운드 실험을 암묵적으로 시작하지 않습니다.

별도 overlay 복사본과 Xvfb에서 스크립트 한 번의 호출로 Passport 홈 화면, 내부 전체 1536×1560, GTK 50%, KVM 활성·VNC 비활성을 확인했습니다. 다른 작업 디렉터리에서 준비 검사도 통과했고, 두 번째 실행 요청은 기존 VM을 재부팅하지 않고 거부됐습니다. SIGTERM 종료 시험에서는 wrapper가 143으로 끝나고 해당 컨테이너도 제거됐습니다. 원래 Passport overlay 해시는 시험 전후 같았습니다.

검증 기록은 [스크립트 실행 검사](emulator/state/start-script-check/verification.json)입니다. 이 검사는 자동 시작·중복 차단·종료 처리에 대한 것이며 앱 배포·사운드 재생 검증 범위를 확대하지 않습니다. 검증 VM은 종료했습니다.

## 20. Git 커밋 전 제외 규칙 준비

사용자 요청으로 `.gitignore`를 먼저 보강했습니다. SDK·보존 VM 이미지·외부 라이브러리·QEMU 원본 checkout·빌드·실행 상태·분석 증거·재분류 백업·배포 QEMU 바이너리를 제외했습니다. 서명 키·개인 키·토큰·기기 로컬 설정·X11 인증 파일·패킷 캡처·로그 등의 패턴도 추가했습니다. 원래 파일을 삭제하거나 스테이징하지 않았습니다.

버전·출처·해시를 기록한 lock JSON, 설정 예시, 실행 스크립트와 실험 소스는 후보로 남겼습니다. PNG·WAV 등 소스 자산 전체를 무시하는 규칙은 쓰지 않았습니다. 실제 Git 규칙으로 제외·유지 사례와 후보 파일을 검사했고, 검사 대상 범위에서 대용량·실행 바이너리·키/토큰 패턴 문제는 발견하지 못했습니다. 이는 완전한 비밀 정보·라이선스 검증을 뜻하지 않습니다.

당시 루트 `.git`은 빈 읽기 전용 디렉터리라 정상 저장소가 아니었습니다. 임시 Git 디렉터리에서 규칙만 검증했으며 실제 Git 초기화·index 변경·커밋은 수행하지 않았습니다. 검사 도구는 실제 저장소가 존재하면 이미 추적된 무시 대상도 확인하도록 했습니다. 자세한 기준과 한계는 [Git 준비 안내](docs/verification/GIT-PREPARATION.ko.md)에 기록했습니다.

## 21. 로컬 인계 문서

사용자 요청으로 루트에 `HANDOFF.md`를 작성했습니다. 이어진 요청에 따라 파일 작성 전에 `.gitignore`에 `/HANDOFF.md`를 추가했고, 제외 규칙 검사에도 해당 경로를 넣었습니다. 인계 문서는 로컬 전용이며 Git 배포 문서에 필수 링크로 추가하지 않았습니다.

인계 내용에는 개발·시뮬레이터 실행 방법, 프로필별 검증 범위, 오디오 미완료 상태, 재분류 자료 보존 원칙, 로컬 제외 자산과 Git 준비 상태를 기록했습니다. 작성 중 실행 중인 BB10 컨테이너가 없음을 확인했고, VM을 새로 시작하거나 실제 Git 초기화·스테이징·커밋을 수행하지 않았습니다.

## 22. GTK 마우스 커서 기본 표시

사용자 요청으로 `emulator/runtime/run.sh`의 GTK 표시 옵션에 `show-cursor=on`을 추가했습니다. 이전에는 이 옵션을 생략해 QEMU 기본값 off를 사용했습니다. 루트 실행 스크립트를 포함해 이 GTK 분기를 사용하는 경로의 다음 실행부터 적용됩니다. Bash 구문 검사를 통과했으며, 이 변경으로 VM을 새로 실행하거나 커서 표시를 화면에서 재검증하지는 않았습니다.

## 23. GitHub 저장소 게시와 MIT 라이선스

사용자 요청으로 GitHub 저장소 `mobiledev-env-BB10`을 **private**으로 만들고 첫 커밋을 push했습니다. 공개 범위는 지정되지 않아 private을 택했습니다. 정상 Git 저장소가 필요했으므로 빈 `.git`에서 `git init`을 실행했고, 스테이징한 69개 파일이 `audit-gitignore.py` 후보 목록과 일치함을 확인했습니다. `HANDOFF.md`와 `a.txt`는 추적하지 않았습니다. 후보에서 비밀 정보 패턴·이메일·홈 경로를 별도로 검색했으며 해당 사항이 없었으나, 이는 모든 비밀 정보·라이선스 문제를 보증하지 않습니다.

라이선스는 검토 후 사용자가 **MIT**를 선택했습니다. 근거는 저장소가 자체 작성 스크립트·문서·작은 예제 중심이고 외부 소스를 포함하지 않으며, 패치 대상인 QEMU `hw/net/pcnet.c`의 헤더(로컬 고정 소스에서 확인)도 MIT 조건이라는 점입니다. Apache-2.0은 특허 조항과 참조 생태계와의 일치가 장점인 대안이었습니다. 저작권자 표기는 사용자의 별도 지정이 없어 git 작성자인 `Peter Yoo`, 연도 2026으로 했습니다.

`LICENSE`를 추가하고 `package.json`에 `license` 필드를 넣었으며(`private`은 유지), README에 제3자 자료(SDK·시뮬레이터 이미지·QEMU 계열·참조 저장소)가 적용 대상이 아님을 명시했습니다. 리버스 엔지니어링 도구는 코드만 MIT이며 대상 이미지를 다룰 권리를 주지 않는다는 단서도 기록했습니다. `dds_abi.h`의 SDK 헤더 파생 정도는 법적으로 확정하지 않았고 최소 선언이라는 사실만 적었습니다.
