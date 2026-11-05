# BB10 자료 분석과 개발 경로

분석 기준일: 2026-11-05. 대상 기기는 Z10과 Passport입니다. BBTube URL은 중복을 제거해 한 번만 분석했습니다. 실제 확인한 소스 commit은 `config/references.lock.json`에 기록했습니다.

## 자료별 판단

| 자료 | 실제 역할 | 이번 기반에 반영한 내용 |
| --- | --- | --- |
| [LianglRen/bb10-native-tools](https://github.com/LianglRen/bb10-native-tools) | PC의 기존 BB10 SDK로 기기에서 실행할 GCC와 Unix 도구를 만드는 스크립트 | SDK 대체재로 사용하지 않고 기기 내 CLI 개발의 참고 자료로 보관 |
| [blackberry/BB10-WebWorks-Framework](https://github.com/blackberry/BB10-WebWorks-Framework) | HTML/CSS/JS와 BB10 네이티브 기능을 연결하는 구형 프레임워크 | 현재 Node에 대한 호환성 조사와 보조 경로로 보관 |
| [AlexeyGurevsky/bbtube](https://github.com/AlexeyGurevsky/bbtube) | C++/Cascades 기반 YouTube 클라이언트 | qmake, BAR descriptor, 네이티브 UI·미디어·데이터 계층 구조 참고 |
| [balika011.hu/blackberry](https://balika011.hu/blackberry/) | 펌웨어, Passport 분해·하드웨어 관련 자료 | 개발 도구와 펌웨어 자료의 용도를 구분 |

### bb10-native-tools

`README.md`, `lib.sh`, `bootstrap/gcc/build.sh`를 확인했습니다. 이 프로젝트는 PC에서 사용할 BB10 크로스 SDK를 새로 제공하는 것이 아닙니다. 이미 설치한 SDK의 환경을 로드하고, BB10에서 실행할 GCC와 GNU 도구 등을 만듭니다.

기기 내 shell에서 간단한 C/C++ 프로그램이나 유틸리티를 실험하려는 경우에 도움이 됩니다. 앱의 UI, BAR 패키징, 배포 서명 문제를 해결하는 기본 환경으로는 충분하지 않습니다. 원본에는 오래된 QNX SVN과 HTTP 다운로드 주소가 있으며 현재 서버 가용성을 검증하지 않았습니다. `build.sh`는 빌드 이후 배포용 로컬 서버까지 실행할 수 있어 이번 구성에서는 실행하지 않았습니다.

원본 설명의 root 불필요 주장은 해당 shell과 사용자 저장 영역에 CLI 도구를 설치하는 절차에 관한 것입니다. 새 미서명 GUI 앱의 설치 조건과 혼동하면 안 됩니다.

### WebWorks

공식 저장소의 README는 Node 0.6.10을 전제로 하며 저장소는 archive 상태입니다. `package.json`에는 Express 2.5.0, Connect 1.7.x 등의 의존성이 있습니다. `configure`는 전역 npm 설치와 sudo를 사용하고 다른 의존성도 버전을 충분히 고정하지 않습니다. 원본 configure는 실행하지 않았습니다.

호스트의 Node 20.20.2로 `build/`와 `lib/`의 정적 API 검사를 실행했습니다. `path.exists`, `path.existsSync`, `util.puts` 호출 중 현재 Node에 없는 호출 지점이 60곳 확인됐습니다. `npm run audit:references`로 다시 확인할 수 있으며 상세 위치는 `build/reference-audit.json`에 기록합니다. 이는 정적 검사 결과이며 의존성 설치나 전체 런타임 검증 결과가 아닙니다.

현재 Node를 그대로 사용하는 사용자 방침을 반영해, 공통 개발 도구는 Node 내장 모듈만 사용합니다. WebWorks를 주력으로 채택하려면 삭제된 API 수정, 의존성 고정, native extension 빌드, 별도 packager 확보를 다뤄야 합니다. 이 프레임워크 저장소만으로 완전한 WebWorks SDK가 준비되지는 않습니다.

대안으로 [Apache Cordova의 BB10 문서](https://cordova.apache.org/archive/docs/en/7.x/guide/platforms/blackberry10/index.html)와 [cordova-blackberry 소스](https://github.com/apache/cordova-blackberry)를 참고할 수 있습니다. 이 경로도 구형 BB10 플랫폼 도구를 대상으로 하므로 최신 Cordova CLI가 그대로 지원한다고 가정하지 않습니다. 호스트 Node를 바꾼다고 기기의 WebKit/JavaScript 엔진이 최신화되지는 않습니다.

### BBTube

`Youtube.pro`, `config.pri`, `Makefile`, `bar-descriptor.xml`, `src/main.cpp`, `src/applicationui.cpp`, 데이터베이스·네트워크·파서 코드를 확인했습니다. 이 앱은 UI의 상당 부분도 C++에서 Cascades 객체로 생성합니다.

참고할 부분은 Cascades 앱 진입점, 탭과 페이지 구성, Qt 네트워크 요청, SQLite 마이그레이션, 앱 설정, 미디어 재생, Invoke 연결입니다. IDE의 `.project/.cproject` 파일이 포함되어 있지만 앱 빌드의 핵심은 qmake 프로젝트와 SDK입니다. `Makefile`이 참조하는 `mk/cs-base.mk` 같은 파일은 SDK에서 제공하는 구성입니다.

새 앱의 최소 예제는 자체 C++/QML 코드로 만들었습니다. BBTube의 앱 ID, authorId, 아이콘, 유튜브 파서와 개발자 정보는 가져오지 않았습니다. 특히 YouTube HTML/내부 응답 및 플레이어 스크립트에 의존하는 파서는 현재 서비스 동작을 보장하지 않습니다. 이번 분석에서 YouTube 재생 성공 여부는 검증하지 않았습니다.

### balika011.hu

확인한 [펌웨어 인덱스](https://balika011.hu/blackberry/firmwares/)에는 Passport와 Priv 디렉터리가 있고, Passport에는 Lineage 및 공식 펌웨어 관련 디렉터리가 있습니다. 최상위 BlackBerry 페이지는 Passport 분해·Android 전환·eMMC 관련 자료도 연결합니다. 확인한 페이지에는 BB10 Native SDK 제공 링크가 없습니다.

따라서 이를 앱 개발 SDK의 출처로 사용하지 않습니다. Android 전환은 BB10 앱 개발과 다른 목표이며, 개발 환경 준비 과정에서 기기 펌웨어를 다운로드하거나 플래시하지 않았습니다.

## 선택한 개발 기반

**C++ / Qt 4.8 / Cascades / QML + BB10 공식 계열 CLI 도구**를 기본 경로로 선택했습니다. 에디터는 VS Code, Vim 등으로 자유롭게 선택할 수 있습니다. 호스트의 Qt 5 qmake는 BB10 앱 빌드에 사용하지 않습니다.

```text
호스트 Node.js 20
  └─ tools/bb10.mjs
       └─ Docker: 고정 SDK 이미지 + tmpfs 소스
            ├─ BB10 qmake → make → qcc/GCC → ARM ELF
            └─ blackberry-nativepackager → unsigned BAR
```

[accupara의 이미지 구성 원본](https://github.com/accupara/docker-images/tree/master/mobile/bb10/ndk)에서 보존 SDK 경로와 환경 변수 구성을 확인했습니다. Docker Hub에서 확인한 이미지 digest를 고정했습니다. 원본 이미지의 IDE와 서비스 실행 명령은 사용하지 않습니다.

host/target을 작업 폴더로 추출해 호스트 실행도 시도했지만, 이 호스트의 XFS inode 번호가 32비트를 넘어서 구형 qmake/qcc에서 파일 탐색이 실패했습니다. 32비트 실행은 작업 샌드박스에서도 SIGSYS로 차단됐습니다. 실제 성공한 경로는 Docker 이미지의 SDK와 tmpfs 임시 소스를 사용하는 방식입니다. 호스트 Node는 유지하고 빌드 도구만 컨테이너에서 실행합니다. 선택적인 호스트 backend는 제공하지만 이 XFS 작업 공간에서 사용할 수 없습니다.

`npm run package`로 ARM ELF와 미서명 BAR 생성에 성공했고, ELF 로더가 `/usr/lib/ldqnx.so.2`임을 확인했습니다. 예제 앱의 실제 화면 실행은 검증하지 않았습니다.

추가로 [XIAZY/blackberry10-toolchain](https://github.com/XIAZY/blackberry10-toolchain)의 Clang/CMake 구성도 조사했습니다. 오래된 GCC를 넘어서는 후속 대안이지만 별도의 링커·ABI 호환성 검증이 필요하므로 이번 기본 빌드는 SDK의 qcc/qmake 경로를 사용합니다. 해당 대안의 Dockerfile은 실행하지 않았습니다.

## 현재 서비스와 설치 제약

BlackBerry의 [공식 안내](https://www.blackberry.com/en/secure-communications/support/end-of-life)는 BB10 관련 레거시 서비스 종료일을 2022-01-04로 명시하고 BlackBerry ID와 World도 영향 대상에 포함합니다. [다운로드 안내](https://www.blackberry.com/en/secure-communications/support/download-notice)도 기존 SWDownloads 서비스 종료와 BB10 지원 종료를 알립니다. 과거 SDK 안내의 신규 BBID 등록·키 발급·온라인 업데이트 절차를 현재 그대로 사용할 수 있다고 가정하지 않습니다.

컴파일과 미서명 BAR 생성은 로컬에서 검증할 수 있습니다. 순정 기기 설치는 해당 기기에 유효한 디버그 토큰 또는 적절한 서명 경로가 있는지 별도로 확인해야 합니다. 기존 키·토큰을 가지고 있다는 사실만으로 현재 유효성이나 새 앱의 서명 가능성을 보장하지 않습니다. 변경된 기기의 설치 경로도 모델, OS, 변경 방식에 따라 다르므로 자동으로 선택하지 않습니다.

후속 개발의 첫 확인 사항은 두 기기의 OS 버전, 개발 모드와 연결 정보, 기존 키/토큰 및 기기 변경 여부입니다. 이 정보가 없어도 소스 작성·크로스 컴파일·패키지 검증은 진행할 수 있습니다.
