"""이모티콘 제작 규격 (PRD.md 의 규격 표를 코드화).

기준이 바뀌면 이 파일만 수정한다. 검수 로직(rules.py)은 이 데이터를 따른다.
"""

# 디바이스 최상위 폴더명 패턴: "[MOBILE] 영문명" / "[DESKTOP] 영문명"
DEVICE_PREFIXES = {
    "[MOBILE]": "mobile",
    "[DESKTOP]": "desktop",
}

# 이모티콘 정보(명칭/설명) 글자수 제한
NAME_KO_MAX = 20      # 국문명
NAME_EN_MAX = 20      # 영문명 (파일명·폴더명과 동일)
DESC_KO_MAX = 120     # 국문 설명
DESC_EN_MAX = 120     # 영문 설명

# 전체 파일 용량 제한 (바이트) — 디바이스 폴더 하나 기준
TOTAL_SIZE_MAX = 2 * 1024 * 1024  # 2MB

# group 폴더 PNG 4종: 파일명 접미사 → (mobile large, mobile small, desktop large, desktop small) 크기
# 크기는 (가로, 세로) px
GROUP_FILES = {
    "_tab_normal.png": {
        "mobile":  {"large": (120, 120), "small": (60, 60)},
        "desktop": {"large": (40, 34),   "small": (40, 34)},
    },
    "_tab_hover.png": {
        "mobile":  {"large": (120, 120), "small": (60, 60)},
        "desktop": {"large": (40, 34),   "small": (40, 34)},
    },
    "_list_thumb.png": {
        "mobile":  {"large": (120, 120), "small": (60, 60)},
        "desktop": {"large": (35, 35),   "small": (35, 35)},
    },
    "_detail_thumb.png": {
        "mobile":  {"large": (200, 200), "small": (72, 72)},
        "desktop": {"large": (50, 50),   "small": (50, 50)},
    },
}

# 대화방 이미지 (영문명_두자리.gif|png) 크기.
#   ※ 대화방 이미지는 없어도 되고(선택), 개수 제한도 없다.
CHAT_SIZES = {
    "mobile":  {"large": (200, 200), "small": (72, 72)},
    "desktop": {"large": (84, 84),   "small": (26, 26)},
}
CHAT_EXTENSIONS = (".gif", ".png")

# 여백 규정 (px) — 콘텐츠(캐릭터) 경계에서 이미지 가장자리까지의 최소 여백.
#   모바일 탭은 배경이 투명이라 알파 채널로, 데스크탑은 단색 배경이라
#   모서리 배경색과 다른 픽셀로 콘텐츠를 감지해 측정한다.
#   (규격 표에 여백이 명시되지 않은 파일은 검사하지 않음)
MARGIN_SPECS = {
    "mobile": {
        "_tab_normal.png": 4,
        "_tab_hover.png": 4,
    },
    "desktop": {
        "_tab_normal.png": 3,
        "_tab_hover.png": 3,
        "_list_thumb.png": 5,
        "_detail_thumb.png": 6,
    },
}
MARGIN_TOLERANCE = 1  # ±1px 허용

# v01: 외곽선(테두리) 색 규정은 삭제되었다 (group 4종 + 대화방 이미지 전체,
#   Mobile/Desktop 공통). 관련 상수(OUTLINE_COLORS/CHAT_OUTLINE_COLOR/OUTLINE_TOLERANCE)와
#   검사 로직(rules.py 의 _check_outline_color 등)을 함께 제거했다.

# 배경이 '투명'으로 규정된 파일 (mobile group 탭 이미지) — 알파 채널 검사 대상
TRANSPARENT_BG_FILES = {
    "mobile": ("_tab_normal.png", "_tab_hover.png"),
    "desktop": (),  # 데스크탑 탭은 배경색 지정(#E5E5E5 등)이라 투명 검사 제외
}

# v01: `_detail_thumb.png` 는 배경색을 고정 규정하지 않고, 배경 있음/없음 상태만
#   알파 채널로 자동 판정해 WARN 으로 공지한다 (Mobile/Desktop, large/small 공통).
BACKGROUND_CHECK_FILES = ("_detail_thumb.png",)

# GIF 반복 재생: "4회 재생 후 멈춤".
#   GIF loop 메타데이터는 저장 도구에 따라 3(추가반복) 또는 4(총횟수)로 기록될 수 있어
#   둘 다 허용한다. 합격 샘플 파일로 실측 후 하나로 좁히는 것을 권장.
GIF_LOOP_ALLOWED = (3, 4)

# 파일명 본체(확장자 제외)에 쓸 수 있는 문자: 영문 소문자·숫자·언더바
#   (PRD "파일명에는 영어 대소문자, 숫자, 언더바만" + "파일명·폴더명 모두 소문자")
FILENAME_STEM_PATTERN = r"^[a-z0-9_]+$"

# 표시명(이모티콘 국문명/영문명/설명)에는 일반 텍스트 특수문자(콜론 등)는 허용,
# 이모지는 불가 — 이모지 판정용 유니코드 블록
EMOJI_PATTERN = (
    "[\U0001F000-\U0001FAFF"   # 이모티콘/픽토그램 대부분
    "\U00002600-\U000027BF"    # 기호·딩뱃 (✅ ☀ ✈ 등)
    "\U0001F1E6-\U0001F1FF"    # 국기
    "\U00002B00-\U00002BFF"    # 화살표·별 기호
    "\uFE0F]"                   # 이모지 변형 선택자
)

# 불필요 파일 (맥OS/윈도우 작업 잔재) — 이름 또는 접두 패턴
JUNK_NAMES = {".ds_store", "thumbs.db", "desktop.ini"}
JUNK_DIR_NAMES = {"__macosx"}
JUNK_PREFIXES = ("._",)   # 맥 리소스 포크
