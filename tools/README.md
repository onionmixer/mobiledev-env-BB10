# 호스트 개발 도구

루트의 [HOWROUSE](../HOWROUSE.md)에 사용자 명령을 모았습니다. 호스트 Node는 명령을 조정하고, BB10 컴파일러·packager는 기본적으로 격리된 SDK 이미지 안에서 동작합니다.

| 도구 | 역할 |
| --- | --- |
| `bb10.mjs` | ARM·x86 빌드·패키징·검증·명시적 배포 |
| `container-task.sh` | SDK 컨테이너의 제한된 CLI 작업 |
| `sdk-run.sh` | 선택적인 추출 SDK 실행. 이 호스트의 기본 빌드 경로가 아님 |
| `fetch-references.mjs`, `audit-references.mjs` | 앱 참조 고정 커밋과 WebWorks 정적 API 검사 |
| `simulator.mjs` | QMP 상태·표시·캡처·키 입력·시험용 네트워크 진단 |
| `maintenance/check-layout.py` | 문서 링크·npm 진입점·재분류된 원본 자료·디스크 연결 검사 |
| `maintenance/audit-gitignore.py` | 실제 ignore 규칙·커밋 후보·대용량/바이너리/일부 키 패턴 검사. staging 없음 |
| `maintenance/reorganize_20261105.py` | 이미 완료한 1회성 전환. 반복 실행 금지 |
| `maintenance/update_layout_paths_20261105.py` | 해당 전환의 유지보수 파일 경로 갱신. 반복 실행 금지 |

에뮬레이터 전용 실행·빌드 스크립트는 [emulator/runtime](../emulator/runtime/)으로, QNX·사운드 연구 소스는 [emulator/research](../emulator/research/)로 분류했습니다.
