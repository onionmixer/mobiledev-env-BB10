# BB10 개발 및 시뮬레이터 작업 공간

BlackBerry Z10·Passport용 앱을 Momentics IDE 없이 개발하기 위한 CLI 환경과, Linux에서 실행하는 BB10 공식 **x86 개발 시뮬레이터**를 준비한 작업 공간입니다. 호스트에 설치된 Node.js를 그대로 사용하며 SDK와 QEMU 실행 라이브러리는 Docker로 격리합니다.

먼저 [HOWROUSE.md](HOWROUSE.md)에서 실행 방법을 확인하세요. 작업 순서, 판단 정정 및 검증 범위는 [HISTORY.md](HISTORY.md)에 기록했습니다. `HOWROUSE`는 요청한 파일명을 그대로 사용했습니다.

## 현재 확인한 상태

| 대상 | 확인 결과 |
| --- | --- |
| C++ / Qt 4.8.6 / Cascades / QML 예제 | ARMv7·x86 컴파일, 미서명 개발 BAR 생성·검증 완료 |
| 예제 런타임 | x86 시뮬레이터 기본 프로필에서 설치·실행 및 Count 0→1 확인 |
| Passport 프로필 | QEMU 자체 GTK 창에서 홈 화면 확인, 사용자도 확인 |
| 최신 표시 구성 | 내부 앱 영역 1440×1440, 전체 프레임버퍼 1536×1560, GTK 창에서만 50% 표시 |
| 연결 방식 | 최신 GTK 실행은 VNC 비활성. 이전 비교 실행은 QEMU VNC + Remmina였으며 RDP가 아님 |
| 사운드 | 호스트 PulseAudio·PCI 카드 확인. ES1370용 게스트 믹서 누락으로 실제 재생 미검증 |
| 실제 Z10·Passport | 설치·실행 미검증. 실제 Passport ARM 펌웨어 부팅도 수행하지 않음 |

기본 SDK는 API `10.3.1.995`, host 도구 `10.3.1.12`입니다. 사용한 호스트 Node는 `20.20.2`이며 버전을 변경하지 않았습니다. WebWorks는 현재 Node에서 제거된 API의 정적 검사만 수행했고, 프레임워크 전체 이식·BBTube 재생은 완료하지 않았습니다.

## 폴더 구성

```text
README.md                  개요·현재 상태·문서 안내
HOWROUSE.md                현재 작업 공간의 실행·빌드·종료 방법
HISTORY.md                 관찰, 정정, 구현, 검증 한계를 구분한 작업 이력
start_emulator_bb10.sh      QEMU GTK 실행·Passport 프로필 자동 선택
tools/                     호스트 Node CLI·SDK 실행·참조 검사·유지보수 도구
docs/                      분석·개발·검증·에뮬레이터 상세 문서
emulator/
  config/                  시뮬레이터·QEMU 버전과 해시 고정 정보
  runtime/                 Dockerfile·QEMU 빌드·실행 스크립트
  tools/                   공식 설치 파일 다운로드·VM 추출 도구
  research/                QNX 파일시스템·PCnet·오디오 실험 소스
  images/                  읽기 전용 공식 VMware 이미지
  lib/                     DXVK 등 실행 라이브러리
  downloads/               보존 설치 파일·다운로드 캐시·외부 소스 자료
  references/              고정 커밋의 QEMU·VMVGA 원본 소스
  build/                   QEMU GUI 소스 작업본·컴파일 결과
  state/                   쓰기 가능한 VM overlay·현재 실행 로그·소켓
  evidence/                이전 시험·분석 증거·RAW 복사본·재분류 백업
examples/                  독립적인 Cascades 시작 예제
config/                    앱 개발 SDK·참조 소스·기기 설정 예시
sdk/                       선택적으로 추출한 앱 개발 NDK
references/                사용자가 제공한 앱·도구 참조 소스
build/                     ARM·x86 앱 결과물과 참조 검사 보고서
```

루트의 `package.json`과 `.gitignore`는 기존 npm 명령 및 생성물 제외 규칙을 유지하기 위해 남겼습니다. 대용량 외부 이미지·빌드 결과·서명 키·로컬 설정은 배포 소스에 포함하지 않습니다. SDK·시뮬레이터·참조 코드의 권리는 각 원저작자에게 있습니다.

커밋 전에는 `python3 tools/maintenance/audit-gitignore.py`로 제외 규칙과 후보 파일을 확인합니다. [Git 준비 안내](docs/verification/GIT-PREPARATION.ko.md)에 제외 대상과 검사 한계를 기록했습니다. 무시된 로컬 증거·스크린샷 링크는 새 clone에 자동 포함되지 않습니다.

## 빠른 실행

현재 호스트에 준비된 환경을 사용합니다.

```bash
npm run doctor
npm run package:simulator
./start_emulator_bb10.sh
```

[start_emulator_bb10.sh](start_emulator_bb10.sh)가 Passport 메뉴를 자동 선택합니다. 빌드 성공과 실제 기기 실행 성공은 별개입니다. 완전히 새로운 호스트의 복구에는 보존 이미지·라이브러리·준비된 USER 복사본이 추가로 필요하며 위 명령만으로 모든 자료가 만들어지는 것은 아닙니다.

## 라이선스와 제3자 자료

이 저장소에 포함된 **자체 작성 파일**(도구·스크립트·예제 앱·문서·설정 lock 파일)은 [MIT License](LICENSE)로 배포합니다. 이 라이선스는 아래 자료에는 적용되지 않으며, 각 자료는 원저작자의 조건을 따릅니다. 이들은 저장소에 포함되지 않고 로컬에서 별도로 준비합니다.

- BlackBerry 10 SDK/NDK, 공식 x86 개발 시뮬레이터 이미지(VMDK), 그 안의 펌웨어·바이너리
- QEMU, QEMU VMVGA, qemu-windows 패치, DXVK, Mesa 등 시뮬레이터 실행 소프트웨어
- `config/references.lock.json`의 참조 저장소(예: `bbtube` Apache-2.0, `accupara/docker-images` GPL-3.0)와 SDK Docker 이미지

`emulator/research/guest/`의 읽기 도구와 `patch_*` 스크립트는 코드 자체만 MIT입니다. 대상이 되는 BlackBerry 이미지와 추출물을 다룰 권리를 부여하지 않으며, 추출한 독점 파일은 재배포하지 않습니다. `emulator/research/audio/dds_abi.h`는 SDK 헤더와 QNX 오디오 DDK 문서에 맞춘 최소 선언입니다. `emulator/research/guest/pcnet-preserve-dwio-experiment.patch`는 MIT 조건의 QEMU `hw/net/pcnet.c`에 대한 패치입니다. 이는 법률 자문이 아니며 외부 자료의 배포 권한은 보장하지 않습니다.

## 상세 문서

- [공유 자료 분석과 기술 선택](docs/analysis/ANALYSIS.ko.md)
- [CLI 개발과 배포 조건](docs/development/DEVELOPMENT.ko.md)
- [실기기 Z10·Passport 점검](docs/development/DEVICES.ko.md)
- [검증 결과](docs/verification/VERIFICATION.ko.md)
- [QEMU 6.2 비교 및 ARM 펌웨어와의 차이](docs/emulator/SIMULATOR.ko.md)
- [VMVGA·PCnet·초기 VNC 시험](docs/emulator/COMPATIBILITY.ko.md)
- [QEMU 자체 창·해상도·사운드](docs/emulator/NATIVE-QEMU.ko.md)
- [폴더 재분류 및 증거 경로 안내](docs/LAYOUT.ko.md)
