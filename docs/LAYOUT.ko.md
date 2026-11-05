# 폴더 재분류와 과거 증거의 위치

2026-11-05에 사용자 요청으로 앱 개발 영역과 에뮬레이터 영역을 나눴습니다. 작업 이력은 루트 [HISTORY](../HISTORY.md), 현재 실행법은 [HOWROUSE](../HOWROUSE.md)에 있습니다.

## 주요 이동표

| 이전 경로 | 현재 경로 |
| --- | --- |
| `tools/vmvga-runtime/` | `emulator/runtime/` |
| `tools/research_guest/` | `emulator/research/guest/` |
| `tools/audio-experiment/` | `emulator/research/audio/` |
| `tools/prepare-simulator.py` | `emulator/tools/prepare-simulator.py` |
| `config/simulator.lock.json`, `qemu-gui.lock.json` | `emulator/config/` |
| `sdk/simulator/` | `emulator/images/` |
| `sdk/vmvga-dxvk/` | `emulator/lib/dxvk/` |
| `downloads/` | `emulator/downloads/` |
| QEMU 관련 `references/qemu-*` | `emulator/references/qemu-*` |
| `build/qemu-gui/` | `emulator/build/qemu-gui/` |
| `build/simulator/` | `emulator/state/stock/` |
| `build/compat/vmvga-*` | `emulator/state/vmvga-*` |
| 나머지 `build/compat/` | `emulator/evidence/` |
| 기존 `docs/*.md` | `docs/analysis/`, `development/`, `verification/`, `emulator/` |

앱 개발 SDK `sdk/bbndk`, 사용자 앱 참조 `references`, 예제 `examples`, 앱 결과 `build/hello-cascades*`는 역할이 이미 구분돼 있어 그대로 두었습니다. 루트의 `package.json`도 npm 명령을 유지하기 위해 남겼습니다.

## 보존 원칙

과거 Evidence·로그·manifest 안의 경로는 작성 당시의 내용입니다. 재분류로 경로가 바뀌었다고 원시 증거 문자열까지 일괄 치환하지 않았습니다. 오래된 경로는 위 표의 **가장 긴 일치 prefix**를 적용해 찾습니다. 예를 들어 `build/compat/vmvga-3d/serial.log`는 `emulator/state/vmvga-3d/serial.log`이고, `build/compat/guest/...`는 `emulator/evidence/guest/...`입니다.

[기계 판독 이동표](../emulator/evidence/layout-migration-20261105/path-map.json)와 [전환 journal](../emulator/evidence/layout-migration-20261105/journal.json)에 전체 기록이 있습니다. 복구용 자료는 같은 디렉터리에 있습니다.

| 보존 자료 | 용도 |
| --- | --- |
| `before/` | 이동 전 도구·문서·설정·README·npm 설정·앱 결과 |
| `overlay-backups/` | backing 경로 변경 전 QCOW2 복사본 |
| `inventory-before.json` | 원래 파일 식별 정보 |
| `plan.json` | 적용 전 이동·디스크 연결 계획 |
| `journal.json` | 실제 이동과 backing 변경·디스크 검사 결과 |
| `verification.json` | 재분류 후 실행·구문·문서 링크 검사 결과 |

이 백업의 QCOW2는 **과거 절대 경로를 포함**합니다. 현재 overlay에 그대로 덮어쓰는 자동 복원 도구가 아닙니다. 복구 시 이동표와 journal을 대조하고 backing 경로를 확인해야 합니다. 파일이 대용량 외부 자료인 경우에도 임의 삭제하거나 원본과 같은 파일이라고 추측해 교체하지 않습니다.

## 현재 실행 상태와 원시 증거

`emulator/state/`는 앞으로 실행 로그·소켓·스크린샷이 새로 생성되는 작업 영역입니다. 이 폴더의 보고서는 과거 실행 기록도 포함하므로 파일의 작성 시각과 scope를 확인합니다. `emulator/evidence/`는 과거 분석·RAW 복사본·시험 산출물·백업을 보존하는 영역입니다.

현재의 상태는 실제 QMP·프로세스로 확인합니다. 예전 JSON의 `running` 값만으로 현재 VM이 켜져 있다고 판단하지 않습니다. 이번 재분류 전 사용자가 VM을 종료했으며, 재분류 검사에서는 별도 `emulator/state/layout-check` 복사본을 사용합니다.

유지보수 스크립트 `tools/maintenance/reorganize_20261105.py`와 경로 갱신 스크립트는 **이번 전환 전용**입니다. 완료 journal이 있으면 반복 실행을 거부합니다. 일반적인 파일 정리 도구나 매번 실행할 setup 단계가 아닙니다.
