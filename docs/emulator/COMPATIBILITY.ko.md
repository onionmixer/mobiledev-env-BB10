# BB10 x86 시뮬레이터 추가 호환성 조사

후속 작업으로 [QEMU 자체 GTK 창](NATIVE-QEMU.ko.md)을 준비했습니다. 해당 경로는 게스트 앱 영역 1440×1440과 전체 프레임버퍼 1536×1560을 유지하고, 호스트 창에만 50%로 표시합니다. 아래 50% USER 설정 시험은 그 이전 VNC 비교 기록입니다.

2026-11-05, 공식 시뮬레이터 10.3.1.2558을 대상으로 실제 부팅을 비교했습니다. **QEMU VMVGA에 PCnet 호환성 수정을 적용해 Cascades 앱의 설치·실행·버튼 동작까지 확인했습니다.** Passport 프로필의 화면 왜곡도 별도 복사본에서 확대 비율을 50%로 바꿔 해소했습니다. 장시간 안정성·기기별 전체 기능은 추가 검증 대상입니다.

## 실행 비교

| 구현 | 가속기·그래픽 | 실제 관찰 |
| --- | --- | --- |
| 배포판 QEMU 6.2 | KVM / TCG, vmware-svga | QNX·기기 메뉴 확인, GUI 미표시 |
| QEMU VMVGA v1.03 | KVM, 3d=off | 잠금 화면까지 진행, 심한 화면 비틀림 |
| QEMU VMVGA v1.03 | KVM, 3d=on, vgpu=9, DXVK 2.7.1, Mesa llvmpipe | 기본 프로필의 정상 형태 홈 화면 확인 |
| 같은 3D 경로 | Keyboard 1440×1440 일반 프로필 | 잠금 화면 및 제스처 안내 반응 확인, 줄 간격·색상 왜곡 잔존 |
| 같은 3D 경로 + PCnet DWIO 수정 | 기본 프로필 | DHCP, BAR 설치·실행, Count 0→1 확인 |
| 같은 경로 + 별도 USER 설정 | Keyboard 1440×1440, 확대 50% | 정상 형태 홈 화면, 출력 768×780 확인 |

기본 프로필 화면: [current.png](../../emulator/state/vmvga-3d/current.png). Passport 시험 화면: [passport-input.png](../../emulator/state/vmvga-3d/passport-input.png). 원시 VGA 캡처는 PPM이며 PNG는 표시를 위해 무손실 변환했습니다. 화면을 보정하거나 합성하지 않았습니다. 프로필의 논리 해상도와 캡처된 호스트 출력 크기는 시뮬레이터 확대·축소 설정 때문에 다릅니다.

실제 앱 실행 결과: [Count 0](../../emulator/state/vmvga-3d/hello-cascades.png), [Count 1](../../emulator/state/vmvga-3d/hello-cascades-count.png). 배포 도구 로그는 `emulator/state/vmvga-3d/deploy-hello-ready.log`입니다. QConn 최적화 연결 실패 후 전체 BAR 전송으로 설치에 성공했으며, SDK는 `result::success`와 실행 PID를 반환했습니다.

3D 로그에는 `SURFACE_DEFINE`, `CONTEXT_DEFINE`, `SURFACE_DMA`, `CLEAR`, `PRESENT` 등 실제 게스트 SVGA3D 요청과 D3D9 처리 기록이 있습니다. Vulkan 장치 열거만으로 성공을 판정한 결과가 아닙니다. 다만 소프트웨어 렌더링 성능과 장시간 안정성은 보증하지 않습니다.

## 구현 선택과 격리

[qemus/qemu-vmvga](https://github.com/qemus/qemu-vmvga)는 기본 QEMU보다 넓은 VMware SVGA/SVGA3D 인터페이스를 구현합니다. 이번 시험에는 [v1.03](https://github.com/qemus/qemu-vmvga/releases/tag/v1.03)의 Linux x86-64 실행 파일을 사용했습니다. upstream QEMU 전체가 같은 기능을 제공한다는 의미는 아닙니다.

| 구성 요소 | 고정 식별자 |
| --- | --- |
| VMVGA 소스 | `073c4dc64e49dd082c70f249dd883cba7ea93f43` |
| QEMU 실행 파일 SHA-256 | `ce36d097fd0954ba64462decd0b6ffc2d5448dcb843b76f3c535bfa790c21599` |
| 자체 보고 버전 | `11.1.1 (qemu-windows 11.2.23)` |
| DXVK native 2.7.1 압축 파일 SHA-256 | `bf0ebbc4bcdee52811b084abbedba51ccaaa304810ec633b76554e91957d2e20` |
| 격리 이미지 | `bb10-vmvga-runtime:v1.03` |

실행 파일의 glibc 요구 사항 때문에 Debian 13 기반 컨테이너를 만들었습니다. 호스트 Ubuntu·Node·커널 옵션은 변경하지 않았습니다. Mesa llvmpipe의 소프트웨어 Vulkan을 사용하므로 호스트 GPU 장치를 전달하지 않았습니다. `/dev/kvm`만 전달하며, 원본 시뮬레이터 디스크는 읽기 전용이고 변경 사항은 개별 QCOW2 overlay에 저장합니다.

컨테이너의 glibc·virglrenderer 처리와 이미지 digest는 [런타임 설명](../../emulator/runtime/README.md), [고정 정보](../../emulator/runtime/runtime.lock.json)에 기록했습니다. DXVK 출처는 `emulator/lib/dxvk/provenance.json`에 있습니다.

## 재실행

현재 호스트에는 이미지와 라이브러리를 준비했습니다. 첫 터미널에서 다음 명령으로 실행합니다.

```bash
npm run simulator:vmvga
```

로컬 VNC는 `127.0.0.1:5912`입니다. 다른 터미널에서 제어합니다.

```bash
node tools/simulator.mjs status --state emulator/state/vmvga-3d
node tools/simulator.mjs screenshot --state emulator/state/vmvga-3d
node tools/simulator.mjs stop --state emulator/state/vmvga-3d
```

guest의 초기 서비스가 준비된 후 앱을 배포합니다. 초기화 도중에는 HTTPS 인증 CGI가 응답을 닫는 현상이 있었고, 초기화 완료 후 같은 명령이 성공했습니다.

```bash
BB10_DEVICE_HOST=127.0.0.1:4443 npm run deploy:simulator
```

실행기는 원본 QEMU 해시를 확인하고 별도 PCnet 수정본을 만든 뒤 읽기 전용으로 컨테이너에 전달합니다. 원본 비교는 `bash emulator/runtime/run.sh 3d kvm stock`입니다. 상세 그래픽 로그는 `BB10_VMVGA_DEBUG=on`, PCnet 추적·패킷 저장은 `BB10_TRACE_PCNET=1`로 켭니다. 기본 실행은 상세 그래픽 로그를 끕니다.

일반 원본 설정의 Passport 프로필은 `menu --state emulator/state/vmvga-3d`로 부팅 메뉴를 연 다음 `resume`, `key 4`, `key ret` 순서로 선택합니다. 각 명령에 같은 `--state`를 전달하고 화면 갱신을 확인합니다. 기본 프로필 복귀는 `reset` 후 메뉴를 선택하지 않고 기다립니다. 최초 서비스 초기화에는 수 분이 걸릴 수 있습니다.

### Passport 화면 보정 시험

기본 66% 확대에서는 출력 폭이 1013으로 설정되며 색상 줄무늬와 비틀림이 생겼습니다. guest의 `mesa` PPS 설정에 `x86pc_BB10Keyboard1440x1440_zoom_factor::0.50`을 추가한 별도 USER 복사본에서는 768×780 출력으로 홈 화면을 정상 표시했습니다. 논리 앱 영역은 1440×1440이며 호스트 표시만 50%입니다. 이 비교는 확대 설정에 따른 우회를 확인한 것이며 정확한 renderer/stride 결함을 단정하지 않습니다.

[Passport 50% 홈 화면](../../emulator/state/vmvga-3d-zoom50/passport-home.png)을 참고하세요. 현재 호스트에 준비한 이 복사본은 다음과 같이 실행합니다. 기본 VM과 같은 VNC/HTTPS 포트를 쓰므로 동시에 실행하지 않습니다.

```bash
npm run simulator:passport
```

다른 터미널에서 다음 순서로 Passport 메뉴를 선택합니다.

```bash
node tools/simulator.mjs menu --state emulator/state/vmvga-3d-zoom50
node tools/simulator.mjs resume --state emulator/state/vmvga-3d-zoom50
node tools/simulator.mjs key 4 --state emulator/state/vmvga-3d-zoom50
node tools/simulator.mjs key ret --state emulator/state/vmvga-3d-zoom50
```

이 호스트의 Remmina에서 조작 가능한 창을 열려면 `remmina -c emulator/evidence/passport-live.remmina`를 실행합니다. 이 연결 프로필은 로컬 VNC `127.0.0.1:5912`만 사용합니다. 앱 영역은 논리 1440×1440, 50% 표시 시 720×720이며, 테두리와 하단 시뮬레이터 상태줄이 포함된 전체 출력은 768×780입니다. 화면 창을 닫아도 VM 종료 명령은 별도로 실행합니다.

설정 변경은 종료한 VM overlay를 RAW로 복사한 `emulator/evidence/guest/passport-zoom50.raw`에만 적용했습니다. 기존 할당 블록 안에 설정을 추가하고 inode의 파일 크기만 바꿨으며, 원본 `current-user.raw`와 공식 VMDK는 보존했습니다. `passport-zoom50-manifest.json`에 두 쓰기 범위와 전후 해시가 있습니다. [실험 도구](../../emulator/research/guest/patch_simulator_zoom.py)는 **이 분석 시점 복사본에만 맞춘 도구**이며 다른 이미지에 일반 적용하지 않습니다.

이 Passport 복사본은 홈 화면 표시까지 확인했지만 앱 재배포가 `peer not authenticated`로 실패했습니다. 관찰 종료 시 시리얼 초기화 기록도 `bbio` 이후 완료되지 않아, 이 복사본을 전체 개발용으로 검증했다고 판단하지 않습니다. 앱 설치·실행·Count 검증은 앞서 설명한 기본 프로필 결과입니다. 실패 원인을 확대 설정 변경 자체로 확정하지 않았습니다.

2D 비교는 `bash emulator/runtime/run.sh 2d`이며 VNC 5911, 별도 overlay를 사용합니다. KVM 대신 TCG를 선택할 수 있게 했지만 **이 VMVGA 조합의 TCG GUI는 미시험**입니다.

## 기존 판단의 정정

게스트 파일시스템과 부팅 스크립트를 확인한 결과, `SERVICE_screen`은 실제 screen 실행 **전에** COM1을 열고 콘솔을 `/dev/ser1`로 전환합니다. 따라서 VGA에 남은 `START SERVICE: screen`은 정확한 중단 함수를 입증하지 않습니다. 이전 QEMU 6.2 시험의 관찰은 “GUI가 표시되지 않고 VGA 문구가 남음”으로 한정합니다.

안전 모드도 `libHwWFDvmware.so`를 사용하므로 VMware 디스플레이 구현을 우회하지 않습니다. 또한 stock QEMU의 TCG도 사용자 모드 I/O에 TSS 권한 검사를 하므로, TCG에서 같은 결과였다는 이유만으로 VMware backdoor 권한 문제를 배제할 수 없습니다. 호스트 `enable_vmware_backdoor=N` 설정은 변경하지 않았습니다. 여러 구현 차이가 있는 시험이므로 성공 원인을 하나의 수정으로 단정하지 않습니다.

## PCnet 원인과 수정 검증

원본 PCnet 추적에서 guest가 DWORD 접근 모드(DWIO)를 켠 뒤 software reset을 읽고, 모드를 다시 켜지 않은 채 DWORD 초기화 값을 쓰는 것을 확인했습니다. QEMU는 reset 때 DWIO를 지우므로 SWSTYLE 설정이 무시되고 CSR1 쓰기는 DWIO 재활성화에만 소비됐습니다. 예를 들어 의도한 주소 `0x78f9ec00` 대신 `0x78f90000`을 읽고 잘못된 16비트 형식·큐 크기로 초기화했습니다.

별도 실행 파일에서 `pcnet_s_reset()`의 DWIO 해제만 막았습니다. 한 바이트를 바꾸며 hard reset은 그대로입니다. 수정 후 `ss32=1`, 수신 큐 64개·송신 큐 128개로 초기화했고 DHCP DISCOVER/OFFER/REQUEST/ACK, guest `10.0.2.15`, HTTPS 및 앱 배포가 동작했습니다. 원본·수정 로그와 패킷은 `pcnet-baseline.log`, `pcnet-patched.log`, `network-baseline.pcap`, `network-patched.pcap`에 있습니다.

이는 [AMD 실제 하드웨어 명세](https://www.amd.com/content/dam/amd/en/documents/archived-tech-docs/datasheets/19436.pdf)의 reset 동작과 다른 **BB10 호환성 우회**입니다. 일반적인 QEMU 버그 수정이라고 주장하지 않으며, 실제 VMware의 해당 동작은 측정하지 않았습니다. [생성 도구](../../emulator/research/guest/patch_pcnet_dwio.py)는 지원하는 원본 SHA-256과 명령 바이트가 일치할 때만 별도 복사본을 만듭니다. [대응 소스 수정](../../emulator/research/guest/pcnet-preserve-dwio-experiment.patch)도 보관했습니다.

수정본 SHA-256: `a3000be09118c82075ecd381d9547a80065481d080a7f67803ba9560b70425dd`. 패치 manifest는 `emulator/evidence/qemu-system-x86_64-bb10-pcnet.json`, REA/Ghidra 증거는 `emulator/evidence/qemu-pcnet-evidence.json`입니다. 게스트 디스크·펌웨어 수정은 이 네트워크 우회에 필요하지 않았습니다.

하단의 `Getting IP...` 문구는 DHCP와 앱 배포 성공 후에도 남았습니다. 해당 문자열을 실제 연결 성공 여부의 판정 기준으로 사용하지 않습니다.

## 남은 호환성 항목

Passport 기본 66% 경로의 왜곡 원인은 아직 확정하지 않았으며, 현재 우회는 50% 확대입니다. 터치 제스처에 따라 안내 화면이 바뀐 것은 확인했지만 전체 키보드·Controller·센서·오디오는 미검증입니다.

GUI 예제 x86 BAR의 컴파일·패키징과 guest 설치·실행·카운터 버튼은 기본 프로필에서 검증했습니다. Z10·Passport 실기기 실행은 별도입니다.

시험 VM은 모두 종료했습니다. 통합 결과는 `emulator/evidence/runtime-report.json`에 기록했으며, 비교용 캡처 3장은 `emulator/evidence/captures/`에 모았습니다.

이번 성공은 **공식 x86 개발 시뮬레이터**에 대한 것입니다. 실제 Passport ARM 펌웨어, Qualcomm 보드·GPU·통신 하드웨어를 에뮬레이션한 결과는 아닙니다.

## 분석 근거

파일시스템은 마운트하지 않고 복사본을 읽었습니다. [추출 도구와 재현 절차](../../emulator/research/guest/README.md)에 QNX6·RCFS·IFS 구조와 소스 근거를 기록했습니다. 게스트 바이너리는 호스트에서 실행하지 않았습니다.

REA/Ghidra로 `fs-rcfs.so`, `guest_info`, PCnet 드라이버를 분석했습니다. Evidence는 `emulator/evidence/rcfs-evidence.json`, `guest-info-evidence.json`, `guest/network/pcnet-evidence.json`에 내보냈고 분석 세션은 닫았습니다. 디컴파일 결과는 복원된 원본 소스가 아닌 분석 자료입니다. PCnet 분석에서는 AMD vendor/device 식별, PROM MAC 읽기와 초기화 IRQ 처리를 확인했으며 VMware OUI 필수 조건은 발견하지 않았습니다.
