# Git 커밋 전 제외 규칙 점검

2026-11-05에 실제 작업 공간을 기준으로 `.gitignore`를 보강했습니다. 이 작업은 파일 삭제·스테이징·커밋을 수행하지 않습니다.

## 커밋에서 제외하는 자료

| 종류 | 주요 경로·패턴 |
| --- | --- |
| 외부 SDK·참조 checkout | `sdk/`, `references/` |
| 앱 결과물·캐시 | `build/`, `.cache/`, `node_modules/`, `__pycache__/` |
| 공식 시뮬레이터와 외부 라이브러리 | `emulator/images/`, `lib/`, `downloads/` |
| 외부 QEMU 소스·컴파일 결과 | `emulator/references/`, `build/`, `runtime/qemu-system-*` |
| VM 상태·증거·백업 | `emulator/state/`, `evidence/` |
| 실수로 다른 위치에 복사한 대용량 자료 | VM 디스크·RAW·ISO·펌웨어 BIN·압축 파일 패턴 |
| 개발용 BAR·컴파일 산출물 | `*.bar`, `*.o`, `*.a`, `*.so*`, `*.dll` 등 |
| 서명 키·개인 키·토큰 | `*.p12`, `*.pfx`, `*.csk`, `*.csj`, `*.pem`, `*.key` 등 |
| 로컬 인증·기기 설정 | `config/local.env`, `device.json`, `.env*`, `.aws/`, Xauthority 등 |
| 실행·통신 기록 | 로그·PID·소켓·PCAP·HAR·DB 패턴 |

`emulator` 행의 `lib/`·`build/`·`evidence/` 등은 해당 `emulator/` 아래 경로를 뜻합니다. 다운로드한 상용·보존 자료와 재분류 전 백업 안의 SDK·바이너리는 소스와 함께 올리지 않습니다. `.gitignore`는 데이터를 삭제하지 않으므로 현재 로컬 실행 자료는 그대로 있습니다.

## 유지하는 자료

루트 문서·실행 스크립트, `tools/`, `examples/`, `docs/`, `emulator/runtime`의 스크립트·Dockerfile, `emulator/research`의 실험 **소스**, `config`·`emulator/config`의 버전·URL·해시 고정 JSON을 유지합니다.

`config/local.env.example`, `config/device.example.json`, `.env.example`·`.env.template` 같은 설정 예시는 제외하지 않습니다. PNG·WAV·QML·XML 전체를 일괄 제외하지 않았습니다. 소스 아이콘·음원까지 사라지지 않도록 하고, 생성 캡처는 경로 단위로 제외합니다. npm lock 파일과 런타임의 `*.lock.json`도 보존 대상입니다.

## 검증 방법

```bash
python3 tools/maintenance/audit-gitignore.py
```

이 도구는 별도 임시 Git 디렉터리와 현재 작업 폴더를 연결해 실제 Git ignore 규칙을 검사합니다. 작업 공간의 `.git`을 생성·수정하거나 파일을 스테이징하지 않습니다. 전역 Git exclude 설정은 검사에서 제외해 이 작업 공간의 규칙을 대조합니다.

실제 제외 대상과 가상으로 지정한 향후 경로, 유지해야 할 소스·설정 예시를 비교합니다. Git의 `check-ignore -v`는 `!` 예외 패턴도 출력할 수 있으므로 **실제 제외 여부는 별도의 quiet 검사 종료 코드로 판정**합니다.

커밋 후보 목록에는 크기·SHA-256을 남기고, 1MiB 초과 파일·실행/압축 바이너리 및 일부 개인 키·토큰 표식을 검사합니다. 키나 토큰의 매칭 내용은 출력하지 않습니다. 이는 제한된 패턴 검사이며 모든 비밀 정보·라이선스 문제를 완전히 검증했다는 뜻은 아닙니다.

보고서는 커밋에서 제외되는 `emulator/evidence/git-preparation/audit.json`, `candidates.json`에 있습니다. 원시 VM·패킷·인증 자료의 내용을 읽어 커밋 보고서에 복사하지 않습니다.

## 현재 저장소 상태와 다음 단계

이 시점의 루트 `.git`은 비어 있는 읽기 전용 디렉터리로, 실제 Git 저장소로 인식되지 않았습니다. 따라서 **실제 index·이미 추적된 파일을 확인하거나 스테이징·커밋한 상태가 아닙니다**. 임시 저장소 검증을 실제 저장소 초기화 완료로 표현하지 않습니다.

정상 Git 저장소가 준비된 뒤 같은 검사 도구를 다시 실행하세요. 실제 저장소에서는 이미 추적 중인데 ignore 규칙에 해당하는 파일도 추가 검사합니다. `.gitignore`를 추가해도 이미 추적된 파일이 자동으로 빠지지는 않습니다. 확인 없이 일괄 `git rm`·index 변경을 수행하지 않습니다.

문서에 남긴 로컬 스크린샷·증거 링크는 무시 대상인 로컬 자료를 가리킬 수 있습니다. 새 clone에는 그 자료가 자동 포함되지 않습니다. 버전·출처·관찰·정정의 텍스트 요약은 README·HISTORY·상세 문서에 유지했습니다.
