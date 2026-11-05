# 개발 환경과 실행 방법

## 검증한 구성

| 구성 요소 | 값 |
| --- | --- |
| 호스트 | Ubuntu 22.04.5 LTS / x86-64 |
| 개발 명령 실행 | 기존 Node.js 20.20.2, Node 내장 모듈만 사용 |
| 기본 SDK 실행 | Docker, `accupara/bbndk` 고정 digest |
| SDK host / target | 10.3.1.12 / 10.3.1.995 |
| qmake / Qt | qmake 2.01a / Qt 4.8.6 |
| 네이티브 패키저 | blackberry-nativepackager 1.11 |
| SDK 컨테이너 Java | 이미지에 보존된 Java 1.7.0_51 |
| 결과물 | ARM ELF32, QNX 로더 `/usr/lib/ldqnx.so.2`, 미서명 개발 BAR |

호스트에 Qt 5 qmake와 Java 8/11/21도 있지만 기본 빌드에는 사용하지 않습니다. Node.js는 기존 호스트 버전을 유지합니다. 개발 명령은 저장소 루트에서 실행합니다.

## SDK 준비

```bash
npm run setup:sdk
npm run doctor
```

처음에는 Docker 레지스트리 접근이 필요합니다. 다운로드 약 2.9GB, 이미지 풀기 후 약 5.5GB입니다. Docker 소켓 접근 권한도 필요합니다. 이후 빌드와 패키징은 `--network=none`으로 실행합니다.

SDK 이미지는 [config/sdk.lock.json](../../config/sdk.lock.json)의 digest로 고정했습니다. 원본 이미지의 기본 명령 대신 `tools/container-task.sh`만 실행하며 GUI, IDE, SSH 서버, supervisor는 시작하지 않습니다. 호출한 사용자의 UID/GID, 읽기 전용 컨테이너 루트, 제한된 bind mount, tmpfs 작업 디렉터리를 사용합니다.

`npm install`, 전역 npm 설치, 호스트 Node 교체는 필요 없습니다. 다운로드한 참고 저장소의 `configure`나 `build.sh`도 실행할 필요가 없습니다.

## 예제 수정과 빌드

```bash
npm run build
npm run package
npm run verify
```

`package`는 먼저 `build`를 실행합니다. 따로 `build`를 실행하는 것은 컴파일만 확인하고 싶을 때입니다. 출력 위치:

```text
build/hello-cascades/
  HelloCascades                 ARM 실행 파일
  HelloCascades-unsigned.bar     미서명 개발 패키지
  verification.json             검증 항목, SDK digest, SHA-256
build/reference-audit.json      WebWorks 정적 검사와 원본 commit
```

주요 편집 대상:

- `examples/hello-cascades/src/`: C++ 앱 진입점과 QML 연결 객체.
- `examples/hello-cascades/assets/main.qml`: Cascades 화면.
- `examples/hello-cascades/HelloCascades.pro`: 소스·헤더·라이브러리 설정.
- `examples/hello-cascades/bar-descriptor.xml`: 앱 ID, 이름, 버전, 패키지 자산과 권한.

현재 CLI는 이 시작 예제 한 개를 대상으로 합니다. 새로운 앱으로 확장할 때 `.pro`의 앱 이름, descriptor의 실행 파일·ID, `tools/bb10.mjs`와 `tools/container-task.sh`의 경로를 함께 변경합니다. SDK 기본 아이콘을 사용하므로 제품용 앱에는 자체 아이콘도 추가합니다.

BB10 API와 Qt 4 문법을 기준으로 작성합니다. 기본 앱은 버튼 호출을 C++의 `Q_INVOKABLE`로 전달하고 `Q_PROPERTY`/notify signal로 화면을 갱신합니다. 후속 앱에서는 비동기 네트워크 작업과 로컬 저장 기능을 별도 C++ 계층으로 추가할 수 있습니다.

예제는 `bb.cascades 1.4`를 사용하며 packager에 `-platformVersion 10.3.1.0`을 전달합니다. manifest의 최소 OS가 이 값인지도 검사합니다. Z10이 이전 OS를 사용한다면 사용 API와 QML import를 검토하고 호환 SDK로 다시 검증해야 합니다.

```bash
BB10_JOBS=4 npm run build
```

기본 작업자 수는 최대 8개입니다. 현재는 작은 시작 예제를 매번 tmpfs에서 빌드하므로 컨테이너 간 증분 빌드는 제공하지 않습니다.

## 실기기 설치

**현재 결과물은 유효한 디버그 토큰에 연결하지 않은 미서명 개발 BAR입니다.** 순정 Z10/Passport에서 바로 설치된다고 가정하지 않습니다. 기기 OS 버전, 개발 모드, IP, 서명/디버그 토큰 조건을 먼저 확인합니다. `npm run deploy`는 SDK 배포 도구를 실행하며 서명을 생성하거나 토큰을 발급하지 않습니다.

기기에 맞는 설치 가능한 BAR를 준비한 후:

```bash
export BB10_DEVICE_HOST=169.254.0.1
read -rsp 'Device password: ' BB10_DEVICE_PASSWORD
export BB10_DEVICE_PASSWORD
npm run deploy
unset BB10_DEVICE_PASSWORD
```

IP는 실제 기기에서 확인한 값으로 바꿉니다. `config/device.example.json`을 `config/device.json`으로 복사해 host를 저장할 수도 있습니다. 비밀번호는 이 JSON에 넣지 않습니다. 기기 두 대는 각각의 IP로 별도 실행합니다.

별도 BAR를 지정하려면:

```bash
npm run deploy -- /absolute/path/to/installable.bar
```

기본 빌드와 달리 `deploy` 명령은 Linux host network를 사용해 지정한 기기에 연결합니다. 이 명령은 사용자가 직접 실행할 때만 기기에 설치를 시도합니다. 비밀번호는 호스트의 Docker 명령 인자에 삽입하지 않고 환경 변수로 전달하지만 SDK/Java 프로세스에서는 기기 연결 인자로 사용되므로 공유 호스트에서는 프로세스 접근 권한을 관리해야 합니다.

기존 유효한 토큰이 있다면 packager의 `-debugToken <token.bar>`를 사용해 author/authorId를 토큰에 맞출 수 있습니다. 현재 자동 명령은 해당 옵션을 넣지 않습니다. 토큰의 기기 PIN·만료·author 일치 여부를 확인한 뒤 패키징 단계를 확장합니다. 단순히 토큰 파일 이름이나 authorId만 바꿔 설치 문제가 해결된다고 가정하지 않습니다.

신규 키/토큰 온라인 발급과 배포 서명은 레거시 서비스 종료 후 가용성을 전제로 하지 않습니다. 미서명 패키지를 허용하도록 변경된 기기의 대체 설치 경로도 이번 작업에서 실행하거나 자동 구성하지 않았습니다. 실기기 검증 항목은 [DEVICES.ko.md](DEVICES.ko.md)에 있습니다.

## 문제 해결과 선택적 호스트 실행

| 증상 | 판단과 조치 |
| --- | --- |
| Docker 소켓 permission denied | 현재 계정의 Docker 접근 권한 확인. 개발 작업 공간에서 권한·그룹을 자동 변경하지 않음 |
| SDK 이미지 없음 | 네트워크가 가능한 상태에서 `npm run setup:sdk` |
| `qcc: no targets defined`, qmake 파일 없음, `stat(".") failed` | 32비트 파일 상태 조회와 큰 inode 충돌 가능. 기본 container backend 사용 |
| 호스트에서 `SIGSYS`/Bad system call | 작업 샌드박스가 구형 32비트 실행을 차단할 수 있음. 허용된 호스트 실행 권한 필요 |
| Node 하위 프로세스 실행의 `EPERM` | 실행 샌드박스의 프로세스 제한 확인. 허용된 호스트 실행으로 점검 |
| `no debug token found` 등 기기 오류 | 컴파일 성공 여부와 별개의 설치 조건. 실제 토큰·서명·기기 상태 확인 |
| QML import 오류·화면 실행 실패 | OS와 API 수준, 로그, 자산 포함 확인. ZIP 검증만으로 QML 실행을 검증할 수 없음 |

선택적으로 SDK host/target만 추출할 수 있습니다.

```bash
npm run setup:sdk -- --extract
BB10_BACKEND=host npm run doctor
```

`tools/sdk-run.sh`는 `sdk/bbndk` 또는 `BB10_SDK_ROOT`와 호스트 Java 8을 사용합니다. 경로는 `config/local.env.example`을 참고합니다. 이 방법은 저번호 inode를 가진 파일 시스템과 32비트 실행 라이브러리가 필요합니다. **현재 작업 공간의 XFS에서는 실패하므로 기본 개발 경로로 사용하지 않습니다.** 다른 파일 시스템에서의 호스트 빌드 전체 과정도 아직 검증하지 않았습니다. 현재 추출본은 분석용으로 보관했고 기본 컨테이너 빌드는 이를 참조하지 않습니다.

셸 설정 파일이나 전역 Node 패키지를 변경하지 않아도 작업 공간을 사용할 수 있습니다.
