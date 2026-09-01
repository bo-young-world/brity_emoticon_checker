# 이모티콘 검수 도구 — 실행 가이드

## 방법 1. exe 로 실행 (검수용 PC — 설치 불필요)

전달받은 `emoticon_checker.exe` 를 **더블클릭**하면 끝. Python·pip 등 아무것도 설치할 필요 없다.

> 처음 실행 시 보안 프로그램이 차단하면 IT 예외 등록 필요 (서명 없는 자체 제작 exe).

## 방법 2. 파이썬으로 실행 (개발 PC)

```powershell
cd brity_automation_emoticon
pip install Pillow          # 최초 1회만 (tkinter 는 윈도우 파이썬에 기본 포함)
python emoticon_checker.py
```

## 사용 순서

1. **[찾아보기…]** 로 검수할 폴더 선택
   - `[MOBILE] 영문명` / `[DESKTOP] 영문명` 폴더를 직접 선택하거나,
   - 그 폴더들이 들어있는 **상위 폴더**를 선택 (→ 두 디바이스 모두 자동 검수)
2. (선택) 이모티콘 정보 입력 — 국문명/영문명(표시명)/설명 → 글자수·이모지 검사 포함
3. **[검수 실행]** — 진행바와 함께 결과가 실시간으로 목록에 쌓임
   - 기본은 문제 항목(FAIL/WARN)만 표시. [통과 항목도 표시] 체크 시 전체 표시
4. **결과 행 클릭** → 우측 미리보기
   - 체크무늬 배경(투명 확인) 위에 이미지 + 판정 색 배너(실제 px) + 탈락 사유
   - 여백 규정 파일은 **빨간 점선(여백 기준선) / 파란 실선(콘텐츠 경계)** 오버레이 표시
   - [탐색기에서 열기] 로 해당 파일 위치로 바로 이동
5. **[CSV 리포트 저장]** — 검수 결과 전체를 엑셀용 CSV 로 저장
6. **[불필요 파일 삭제]** — .DS_Store, __MACOSX, Thumbs.db 등 잔재 일괄 삭제

### 판정 의미

| 표시 | 의미 |
|------|------|
| 🔴 FAIL | 규격 위반 — 수정 필요 (구조/파일명/크기/용량/GIF 무한반복/정보 등) |
| 🟠 WARN | 확인 필요 — 측정 기반 항목(여백/외곽선 색/투명 배경) 및 잔재 파일 |
| 🟢 PASS | 통과 |

## CLI 로 실행 (자동화/원격 검수)

```powershell
python emoticon_checker.py --check "C:\작업\[MOBILE] happy" --csv output\결과.csv
```

- 문제 항목만 콘솔에 출력, FAIL 이 하나라도 있으면 **종료코드 1** (배치/스크립트 연동용)
- exe 도 동일: `emoticon_checker.exe --check "폴더" --csv 결과.csv`

## exe 만들기 (개발 PC — 최초/업데이트 시)

```powershell
cd brity_automation_emoticon
pip install Pillow pyinstaller   # 최초 1회
build.bat                        # → dist\emoticon_checker_v{버전}.exe 생성 (예: emoticon_checker_v0.3.0.exe)
```

파일명에 `emoticon_checker.py` 의 `APP_VERSION` 이 자동으로 붙어서, 재빌드해도 기존 exe를
덮어쓰지 않고 새 버전 파일이 따로 생긴다 (구버전을 최신으로 착각하는 실수 방지).
생성된 `dist\emoticon_checker_v{버전}.exe` 파일 **하나만** 검수 PC 에 복사하면 배포 끝.

## 문제 해결

| 증상 | 조치 |
|------|------|
| exe 실행이 차단됨 | 보안 프로그램 예외 등록 (IT 요청) |
| "검수 대상을 찾지 못했습니다" | 폴더명이 `[MOBILE] 영문명` / `[DESKTOP] 영문명` 형식인지 확인 |
| 파이썬 실행 시 `No module named PIL` | `pip install Pillow` |
| 여백/외곽선 판정이 이상함 | 측정 기반(WARN)이라 오차 가능 — `src/spec.py` 의 `MARGIN_TOLERANCE`, `OUTLINE_TOLERANCE` 조정 |
| 규격 수치가 바뀜 | `src/spec.py` 만 수정 (크기/여백/색/용량 전부 여기서 관리) |

검사 항목 전체 목록과 판정 기준은 [readme.md](readme.md), 규격 원문은 [PRD.md](PRD.md) 참고.
