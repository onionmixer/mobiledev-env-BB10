# BB10 x86 시뮬레이터

현재 실행법은 루트 [HOWROUSE](../HOWROUSE.md), 관찰·판단 정정은 [HISTORY](../HISTORY.md), 직접 GTK 창은 [상세 문서](../docs/emulator/NATIVE-QEMU.ko.md)를 참고합니다.

| 경로 | 역할 |
| --- | --- |
| `config/` | 원본 이미지와 QEMU 빌드 고정 정보 |
| `runtime/` | 격리 런타임·빌드·실행 스크립트 |
| `tools/` | 공식 설치 파일 다운로드·추출 |
| `research/` | 파일시스템 읽기 및 격리된 PCnet·오디오 실험 |
| `images/`, `lib/`, `downloads/`, `references/` | 외부 이미지·실행 라이브러리·보존 자료·원본 소스 |
| `build/` | QEMU GUI 컴파일 작업본·결과 |
| `state/` | 각 VM의 쓰기 overlay·현재 로그·소켓 |
| `evidence/` | 과거 시험과 분석 증거·RAW 복사본·이전 구조 백업 |

현재 준비된 호스트에서 `npm run simulator:passport:gui`로 실행하고 기기 메뉴 4번을 선택합니다. 실제 Passport ARM 펌웨어가 아니라 공식 x86 시뮬레이터입니다. 사운드 재생은 검증이 완료되지 않았습니다. 상태 제어에는 `--state emulator/state/vmvga-gtk-passport`를 사용합니다.

이전 증거에 남은 경로는 [재분류 안내](../docs/LAYOUT.ko.md)로 찾습니다. 원본 이미지·RAW 분석 복사본과 쓰기 overlay를 서로 교체하지 않습니다.
