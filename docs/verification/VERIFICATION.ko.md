# 개발 기반 검증 기록

검증일: 2026-11-05. 작업 호스트: Ubuntu 22.04.5 x86-64, Node.js 20.20.2. 대상 기기: Z10과 Passport. 기기는 연결하지 않았습니다.

| 검증 | 결과 |
| --- | --- |
| 참고 저장소 5개의 commit 고정·재확인 | 통과 |
| WebWorks 현재 Node 정적 API 검사 | 실행 완료, 제거된 API 호출 60곳 확인 |
| Node 개발 스크립트 구문 검사 | 통과 |
| Bash SDK/컨테이너 스크립트 구문 검사 | 통과 |
| 고정 digest의 SDK 이미지 다운로드 | 완료 |
| 컨테이너 `doctor` | 통과, ARM target·qmake/Qt 4.8.6·Java·packager 확인 |
| C++ 컴파일·Qt moc·링크 | 통과 |
| ARM ELF 및 QNX 로더 확인 | 통과 |
| 미서명 개발 BAR 생성 | 통과 |
| BAR ZIP 무결성·manifest·QML·실행 파일 확인 | 통과 |
| 최소 OS 10.3.1.0 및 ARM 패키지 아키텍처 | 통과 |
| 패키지 안 실행 파일과 빌드 파일의 바이트 일치 | 통과 |
| 별도 `npm run verify` 명령 | 통과 |
| 시뮬레이터용 x86 ELF·BAR 생성 및 검증 | 통과 |
| 공식 x86 시뮬레이터 이미지 확보·해시·디스크 추출 | 통과 |
| QEMU KVM/TCG에서 QNX 부팅·기기 선택 메뉴 | 확인 |
| QEMU 6.2 기본 vmware-svga에서 BB10 GUI 표시 | 미표시; VGA 마지막 문구만으로 중단 함수는 확정할 수 없음 |
| QEMU VMVGA / KVM / DXVK / llvmpipe | 기본 프로필 홈 화면 표시 확인 |
| VMVGA / Passport 1440×1440 프로필 | 잠금 화면·터치 반응 확인, 화면 왜곡 잔존 |
| Passport 프로필 / 별도 USER 복사본 확대 50% | 768×780 출력으로 홈 화면 왜곡 해소 |
| QEMU 자체 GTK / Passport 내부 확대 100% | 내부 전체 1536×1560 유지, 호스트만 50%, VNC 비활성 확인 |
| QEMU GTK 홈 화면 | 사용자 확인 후 사용자가 종료. 재분류 후에는 별도 복사본으로 재검증하고 종료 |
| ES1370 / PulseAudio 진단 | 호스트 연결·PCI 카드 확인, 게스트 AK4531 믹서 누락으로 재생 미확인 |
| VMVGA + PCnet DWIO 호환성 수정 | DHCP 10.0.2.15 및 SDK BAR 설치·실행 확인 |
| Cascades 예제 GUI 이벤트 | Count 버튼 터치 후 0→1 증가 확인 |
| 서명·디버그 토큰 발급/갱신 | 수행하지 않음 |
| Z10·Passport 설치·화면·버튼 동작 | 미검증 |
| WebWorks 전체 빌드·BBTube 재생 | 미검증 |

실제 출력:

- `build/hello-cascades/HelloCascades`: ARM ELF32 little-endian, 468,979 bytes.
- `build/hello-cascades/HelloCascades-unsigned.bar`: 개발용 미서명 BAR.
- `build/hello-cascades/verification.json`: 검증 시각과 아티팩트 SHA-256, SDK digest.
- `build/reference-audit.json`: 원본 commit과 WebWorks 정적 API 검사 결과.

재현 명령:

```bash
npm run setup:sdk
npm run doctor
npm run package
npm run verify
npm run audit:references
```

호스트 직접 실행에서는 XFS의 큰 inode 때문에 qmake 파일 조회와 qcc target 탐색이 실패했습니다. 현재 기본 경로는 이미지의 SDK와 tmpfs 임시 소스를 사용하는 컨테이너 실행이며, 이 경로로 실제 빌드와 패키징에 성공했습니다. 샌드박스에서 32비트 실행 및 일부 하위 프로세스가 SIGSYS/EPERM으로 차단된 검사는 허용된 호스트 실행으로 다시 수행했습니다.

패키징 검증은 실제 BB10 런타임 테스트를 대체하지 않습니다. 기기별 OS 버전과 설치 조건을 확인한 뒤 [기기 점검표](../development/DEVICES.ko.md)에 따라 실기기 검증을 진행할 수 있습니다.

QEMU 시뮬레이터 실험의 상세 결과와 한계는 [SIMULATOR.ko.md](../emulator/SIMULATOR.ko.md)에 기록했습니다. 이 결과는 모든 QEMU 버전의 실행 가능성을 판정한 것이 아닙니다.
