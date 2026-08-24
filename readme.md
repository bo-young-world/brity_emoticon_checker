# 이모티콘 검수 윈도우 애플리케이션

이모티콘 폴더를 [PRD.md](PRD.md) 규격에 따라 자동 검수하는 Windows GUI 프로그램.
PyInstaller 로 단일 exe 를 만들어 배포하므로 **대상 PC 에 Python 설치가 필요 없다.**

## 검사 항목

| 항목 | 내용 | 판정 |
|------|------|------|
| 구조 | `[MOBILE]/[DESKTOP] 영문명` > `group/large·small`(필수), `large·small`(대화방, 선택) | FAIL |
| 파일명 | 전부 소문자 + **영문/숫자/언더바만**(특수문자 불가). group PNG 4종은 `영문명_tab_normal.png` 등 고정, 대화방은 제안서와 동일하면 자유 | FAIL |
| 필수 파일 | group 폴더 PNG 4종 존재 (tab_normal/tab_hover/list_thumb/detail_thumb) | FAIL |
| 이미지 크기 | PRD 규격 표의 px 와 픽셀 단위 대조 | FAIL |
| GIF 반복 | 4회 재생 후 멈춤 (무한 반복 = FAIL) | FAIL/WARN |
| 투명 배경 | 모바일 탭 이미지 알파 채널 검사 | WARN |
| 여백 | 콘텐츠 경계 실측 — 모바일 탭 4px / 데스크탑 탭 3px·list_thumb 5px·detail_thumb 6px (±1px, 4방향 실측값 표시) | WARN |
| 외곽선 색 | 경계 안쪽 1px 링 색 중앙값을 규정색(#A5A5A5/#999999/#FFFFFF)과 대조 — 실측 색상 표시 | WARN |
| 전체 용량 | 디바이스 폴더당 2MB 이내 | FAIL |
| 불필요 파일 | .DS_Store, __MACOSX, Thumbs.db 등 탐지 + 원클릭 삭제 | WARN |
| 정보 | 국문명 20자 / 영문명 20자 / 설명 120자 + **이모지 사용 불가** (GUI 입력 시) | FAIL |

- 대화방 GIF 는 **없어도 되고 개수 제한 없음** (있으면 규격 검사)
- **표시명과 파일명은 별개** — 표시명(예: "KKKK Keuala : Reboot")은 대문자·일반 특수문자
  가능(이모지 불가), 파일명·폴더 영문명은 소문자/숫자/언더바만
- 외곽선 **두께**는 자동 판정이 어려워 눈검수 대상 (색상은 자동 검사, 규격은 PRD 참고)
- 규격 수치가 바뀌면 `src/spec.py` 만 수정하면 된다

## 사용법

> 단계별 상세 실행 방법은 **[RUN_GUIDE.md](RUN_GUIDE.md)** 참고.
> 배포본은 `emoticon_checker.exe` **더블클릭**으로 실행 (설치·Python 불필요).

```powershell
# GUI (기본)
python emoticon_checker.py

# CLI — 자동화/원격 검수용 (FAIL 있으면 종료코드 1)
python emoticon_checker.py --check "C:\작업\[MOBILE] happy" --csv output\결과.csv
```

폴더는 `[MOBILE] 영문명` 폴더를 직접 선택하거나, 그런 폴더들이 들어있는 상위 폴더를
선택하면 된다 (상위 폴더 선택 시 [MOBILE]/[DESKTOP] 모두 자동 검수).

### GUI 화면 구성

- **검수 진행 실시간 표시** — 검수가 백그라운드로 돌면서 진행바가 차오르고,
  결과가 나오는 즉시 목록에 한 줄씩 추가된다 (큰 폴더도 화면이 멈추지 않음)
- **이미지 미리보기 (우측 패널)** — 결과 행을 클릭하면 해당 이미지가
  체크무늬 배경(투명 영역 확인용) 위에 표시되고:
  - 이미지 상단 배너와 테두리에 **판정 색**(빨강=불합격/주황=확인/초록=통과)과
    **실제 크기(px)**, 그 아래에 **탈락 사유**가 표시된다
  - [탐색기에서 열기]로 해당 파일 위치를 바로 열 수 있다
- 폴더 요약 행은 PASS/WARN/FAIL 집계를 보여주고, 기본은 문제 항목만 표시
  ([통과 항목도 표시] 체크 시 전체 표시)

## 폴더 구조

```
brity_automation_emoticon/
├── readme.md                 # 이 문서
├── emoticon_checker.py       # 진입점 (tkinter GUI)
├── requirements.txt          # 이 도구 전용 의존성 (Pillow 등)
├── emoticon_checker.spec     # PyInstaller 빌드 스펙
├── build.bat                 # exe 빌드 스크립트 (더블클릭)
├── docs/                     # ★ 검수 기준 문서를 여기에 업로드
├── src/                      # 검수 규칙·이미지 분석 로직
├── assets/                   # 앱 아이콘 등 리소스
└── output/                   # 검수 리포트 저장 위치 (실행 시 생성, git 미추적)
```

## 개발/빌드 (인터넷 되는 PC)

```powershell
cd brity_automation_emoticon
pip install -r requirements.txt

# 개발 중 실행
python emoticon_checker.py

# exe 빌드 → dist\emoticon_checker.exe 생성
build.bat
```

## 배포 (오프라인 PC)

`dist\emoticon_checker.exe` **파일 하나만 복사**하면 끝. Python·pip 불필요.

> 서명 없는 자체 제작 exe 라 보안 프로그램이 첫 실행을 차단할 수 있음.
> 차단되면 IT 예외 등록 필요.

## 다음 단계 (TODO)

- [x] 검수 기준 문서 (PRD.md)
- [x] 검수 규칙 구현 (`src/spec.py` + `src/rules.py`)
- [x] GUI 구현 (폴더 선택, 결과 트리, CSV 저장, 불필요 파일 삭제)
- [x] CLI 모드 (`--check`) + 샘플 폴더 검증
- [ ] 실제 이모티콘 폴더로 검증 (특히 **GIF loop 값 실측** — `src/spec.py` 의 `GIF_LOOP_ALLOWED` 보정)
- [ ] `build.bat` 으로 exe 빌드 후 배포
