"""이모티콘 검수 규칙 — 디바이스 폴더 하나를 받아 검수 결과 목록을 돌려준다.

사용:
    from src.rules import check_device_folder, Finding
    findings = check_device_folder(r"C:\\작업\\[MOBILE] happy")

결과(Finding)는 PASS / WARN / FAIL 세 단계.
규격 수치는 spec.py 에서만 관리한다.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Tuple

from PIL import Image

from . import spec

PASS, WARN, FAIL = "PASS", "WARN", "FAIL"


@dataclass
class Finding:
    level: str      # PASS / WARN / FAIL
    category: str   # 검사 항목 (구조/파일명/크기/용량/GIF/투명배경/정보/불필요파일)
    target: str     # 대상 (상대 경로 또는 항목명)
    message: str    # 사람이 읽는 설명


# ---------------------------------------------------------------- 폴더 해석 --

def parse_device_folder(folder: Path) -> Optional[Tuple[str, str]]:
    """'[MOBILE] happy' → ('mobile', 'happy'). 패턴이 아니면 None."""
    name = folder.name.strip()
    for prefix, device in spec.DEVICE_PREFIXES.items():
        if name.upper().startswith(prefix):
            en_name = name[len(prefix):].strip()
            if en_name:
                return device, en_name
    return None


def find_device_folders(root: Path) -> List[Path]:
    """선택한 폴더에서 검수 대상 디바이스 폴더들을 찾는다.

    - root 자체가 '[MOBILE] xxx' 형태면 그 폴더 하나
    - 아니면 바로 아래에서 '[MOBILE] xxx' / '[DESKTOP] xxx' 폴더들을 수집
    """
    if parse_device_folder(root):
        return [root]
    return sorted(
        d for d in root.iterdir()
        if d.is_dir() and parse_device_folder(d)
    )


def total_size_kb(folders: List[Path]) -> float:
    """선택한 디바이스 폴더들(예: MOBILE+DESKTOP) 전체 파일 용량 합계 (KB).

    검수 결과 맨 처음에 표시하는 참고용 요약 — 디바이스 폴더별 2MB FAIL 판정과는 별개.
    """
    total = sum(f.stat().st_size for d in folders for f in d.rglob("*") if f.is_file())
    return total / 1024


# ------------------------------------------------------------------ 검사들 --

def _is_junk(path: Path) -> bool:
    n = path.name.lower()
    return (n in spec.JUNK_NAMES
            or n in spec.JUNK_DIR_NAMES
            or any(n.startswith(p) for p in spec.JUNK_PREFIXES))


def _image_size(path: Path) -> Optional[Tuple[int, int]]:
    try:
        with Image.open(path) as im:
            return im.size
    except Exception:
        return None


_EMOJI_RE = re.compile(spec.EMOJI_PATTERN)
_STEM_RE = re.compile(spec.FILENAME_STEM_PATTERN)


def _check_info_texts(en_name: str, info: dict, out: List[Finding]) -> None:
    """명칭/설명 글자수 + 이모지 + 영문명 규칙. info 는 GUI 입력(없는 키는 검사 생략).

    표시명(국문명/영문명)에는 콜론 같은 일반 특수문자는 허용, 이모지는 불가.
    폴더에서 딴 en_name(파일명 접두)은 파일명 문자 규칙(소문자·숫자·언더바)을 따라야 한다.
    """
    limits = [
        ("국문명", info.get("name_ko"), spec.NAME_KO_MAX),
        ("영문명(표시명)", info.get("name_en"), spec.NAME_EN_MAX),
        ("영문명(폴더)", en_name, spec.NAME_EN_MAX),
        ("국문 설명", info.get("desc_ko"), spec.DESC_KO_MAX),
        ("영문 설명", info.get("desc_en"), spec.DESC_EN_MAX),
    ]
    for label, value, max_len in limits:
        if value is None or value == "":
            continue
        n = len(value)
        if n > max_len:
            out.append(Finding(FAIL, "정보", label, f"{n}자 — {max_len}자 이내여야 함: {value!r}"))
        else:
            out.append(Finding(PASS, "정보", label, f"{n}자 (≤{max_len})"))
        emojis = _EMOJI_RE.findall(value)
        if emojis:
            out.append(Finding(FAIL, "정보", label,
                               f"이모지 사용 불가: {' '.join(emojis[:5])} — 일반 텍스트 특수문자만 허용"))

    # 폴더 영문명 = 파일명 접두 → 파일명 문자 규칙 적용 (소문자·숫자·언더바)
    if not _STEM_RE.match(en_name):
        bad = sorted({ch for ch in en_name if not re.match(r"[a-z0-9_]", ch)})
        out.append(Finding(FAIL, "정보", "영문명(폴더)",
                           f"허용되지 않는 문자 {bad} 포함: {en_name!r} — "
                           "파일명·폴더명은 영문 소문자/숫자/언더바만 가능"))


def _check_structure(device_dir: Path, out: List[Finding]) -> None:
    # v02: group/large, group/small 뿐 아니라 대화방(large/small) 폴더도 필수.
    #   (안의 이미지 파일 자체는 여전히 선택 — _check_chat_files 참고)
    for rel in ("group/large", "group/small", "large", "small"):
        if not (device_dir / rel).is_dir():
            out.append(Finding(FAIL, "구조", rel, "필수 폴더 없음"))
        else:
            out.append(Finding(PASS, "구조", rel, "폴더 있음"))

    expected_top = {"group", "large", "small"}
    for d in device_dir.iterdir():
        if d.is_dir() and d.name not in expected_top and not _is_junk(d):
            out.append(Finding(WARN, "구조", d.name, "규격에 없는 폴더 — 필요한지 확인"))

    _check_group_depth(device_dir, out)


def _check_group_depth(device_dir: Path, out: List[Finding]) -> None:
    """group 폴더 하위 뎁스 검사 (v02).

    - group 바로 밑에 파일이 있으면 FAIL (group/large 또는 group/small 안에 있어야 함)
    - group 바로 밑에 large/small 이 아닌 폴더가 있으면 FAIL
    - group/large, group/small 안에 또 하위 폴더가 있으면 FAIL (이미지 파일만 있어야 함)
    """
    gdir = device_dir / "group"
    if not gdir.is_dir():
        return  # 이미 위에서 FAIL 처리됨

    for item in gdir.iterdir():
        if _is_junk(item):
            continue
        if item.is_file():
            out.append(Finding(FAIL, "구조", f"group/{item.name}",
                               "group 폴더 바로 밑에 파일이 있음 — group/large 또는 group/small 안에 있어야 함"))
        elif item.is_dir() and item.name not in ("large", "small"):
            out.append(Finding(FAIL, "구조", f"group/{item.name}",
                               "group 폴더 밑에 예상치 못한 하위 폴더 — large/small 만 허용"))

    for sub in ("large", "small"):
        sdir = gdir / sub
        if not sdir.is_dir():
            continue
        for item in sdir.iterdir():
            if item.is_dir() and not _is_junk(item):
                out.append(Finding(FAIL, "구조", f"group/{sub}/{item.name}",
                                   f"group/{sub} 안에 폴더가 있음(깊이 오류) — 이미지 파일만 있어야 함"))


def _check_group_files(device: str, en_name: str, device_dir: Path, out: List[Finding]) -> None:
    for sub in ("large", "small"):
        gdir = device_dir / "group" / sub
        if not gdir.is_dir():
            continue  # 구조 검사에서 이미 FAIL

        expected = {f"{en_name}{suffix}": spec.GROUP_FILES[suffix][device][sub]
                    for suffix in spec.GROUP_FILES}
        found = {f.name: f for f in gdir.iterdir() if f.is_file() and not _is_junk(f)}

        for fname, size in expected.items():
            rel = f"group/{sub}/{fname}"
            f = found.pop(fname, None)
            if f is None:
                # 대소문자만 다른 파일이 있는지 확인
                ci = next((v for k, v in list(found.items()) if k.lower() == fname), None)
                if ci is not None:
                    found.pop(ci.name)
                    out.append(Finding(FAIL, "파일명", f"group/{sub}/{ci.name}",
                                       f"파일명 대소문자 불일치 — {fname} 로 수정 (모두 소문자)"))
                    f = ci
                else:
                    out.append(Finding(FAIL, "파일", rel, "필수 파일 없음"))
                    continue
            actual = _image_size(f)
            if actual is None:
                out.append(Finding(FAIL, "크기", rel, "이미지를 열 수 없음 (손상/포맷 확인)"))
            elif actual != size:
                out.append(Finding(FAIL, "크기", rel,
                                   f"{actual[0]}×{actual[1]}px — 규격 {size[0]}×{size[1]}px"))
            else:
                out.append(Finding(PASS, "크기", rel, f"{size[0]}×{size[1]}px OK"))

            # 배경 투명 규정 파일: 알파 채널 존재 + 실제 투명 픽셀 여부
            suffix = fname[len(en_name):]
            if suffix in spec.TRANSPARENT_BG_FILES.get(device, ()):
                _check_transparency(f, rel, out)

            # 여백 규정 파일: 콘텐츠 경계에서 가장자리까지 실측
            required_margin = spec.MARGIN_SPECS.get(device, {}).get(suffix)
            if required_margin is not None:
                _check_margin(f, rel, required_margin, out)

            # 배경 있음/없음 자동 판정 파일(detail_thumb): 고정 색상 대신 상태만 WARN 공지
            if suffix in spec.BACKGROUND_CHECK_FILES:
                _check_background_presence(f, rel, out)

        for extra in found.values():
            out.append(Finding(WARN, "파일", f"group/{sub}/{extra.name}",
                               "규격에 없는 파일 — 불필요 시 삭제"))


def _content_mask(rgba: Image.Image) -> Image.Image:
    """콘텐츠(캐릭터) 영역 마스크 (L 모드, 콘텐츠=255).

    - 알파 채널에 투명 픽셀이 있으면: 알파 > 8 인 영역을 콘텐츠로 본다.
    - 그 외(단색 배경): 좌상단 모서리 색을 배경으로 보고, 그와 다른 픽셀을 콘텐츠로 본다.
    """
    alpha = rgba.getchannel("A")
    if alpha.getextrema()[0] < 255:
        return alpha.point(lambda a: 255 if a > 8 else 0)
    from PIL import ImageChops
    bg = Image.new("RGBA", rgba.size, rgba.getpixel((0, 0)))
    diff = ImageChops.difference(rgba, bg).convert("L")
    return diff.point(lambda v: 255 if v > 10 else 0)


def _content_margins(f: Path) -> Optional[Tuple[int, int, int, int]]:
    """콘텐츠 경계 기준 여백 (left, top, right, bottom). 감지 실패 시 None."""
    try:
        with Image.open(f) as im:
            rgba = im.convert("RGBA")
        w, h = rgba.size
        bbox = _content_mask(rgba).getbbox()
        if not bbox:
            return None
        left, top, right, bottom = bbox
        return (left, top, w - right, h - bottom)
    except Exception:
        return None


def _check_margin(f: Path, rel: str, required: int, out: List[Finding]) -> None:
    margins = _content_margins(f)
    if margins is None:
        out.append(Finding(WARN, "여백", rel, "콘텐츠를 감지하지 못해 여백 측정 불가 — 눈으로 확인"))
        return
    l, t, r, b = margins
    tight = min(margins)
    detail = f"실측 좌{l}/상{t}/우{r}/하{b}px (규정 {required}px)"
    if tight < required - spec.MARGIN_TOLERANCE:
        out.append(Finding(WARN, "여백", rel, f"여백 부족 — {detail}. 콘텐츠가 가장자리에 너무 붙음"))
    elif tight > required + spec.MARGIN_TOLERANCE:
        out.append(Finding(WARN, "여백", rel, f"여백 과다 — {detail}. 콘텐츠가 규격보다 작게 배치됨"))
    else:
        out.append(Finding(PASS, "여백", rel, f"여백 OK — {detail}"))


def _check_transparency(f: Path, rel: str, out: List[Finding]) -> None:
    try:
        with Image.open(f) as im:
            rgba = im.convert("RGBA")
            alpha_min = rgba.getchannel("A").getextrema()[0]
        if alpha_min == 255:
            out.append(Finding(WARN, "투명배경", rel, "투명 픽셀 없음 — 배경 투명 규정 확인"))
        else:
            out.append(Finding(PASS, "투명배경", rel, "투명 배경 OK"))
    except Exception as e:
        out.append(Finding(WARN, "투명배경", rel, f"검사 실패: {e}"))


def _check_background_presence(f: Path, rel: str, out: List[Finding]) -> None:
    """`_detail_thumb.png` 전용 — 배경 있음/없음만 자동 판정해 WARN 으로 공지한다.

    v01: 고정 배경색 규정을 없애고, 알파 채널 최솟값으로 완전 투명(=배경 없음) 여부만
    판단한다. FAIL 이 아니라 상태 공지용 WARN — 실제 화면은 눈으로 확인한다.
    """
    try:
        with Image.open(f) as im:
            rgba = im.convert("RGBA")
            alpha_min = rgba.getchannel("A").getextrema()[0]
        if alpha_min == 255:
            out.append(Finding(WARN, "배경", rel, "배경색 있음 — 눈으로 확인"))
        else:
            out.append(Finding(WARN, "배경", rel, "배경색 없음(투명) — 눈으로 확인"))
    except Exception as e:
        out.append(Finding(WARN, "배경", rel, f"검사 실패: {e}"))


def _check_chat_files(device: str, en_name: str, device_dir: Path, out: List[Finding]) -> None:
    """대화방 이미지 — 없어도 되고(선택) 개수 제한 없음. 있으면 규격 검사.

    파일명은 제안서와 동일하면 되고 형식(숫자 위치 등)은 자유 — 정렬용일 뿐.
    프로그램은 파일명 문자 규칙(소문자/숫자/언더바)과 이미지 규격만 검사한다.
    """
    counts = {}
    for sub in ("large", "small"):
        cdir = device_dir / sub
        if not cdir.is_dir():
            continue
        files = [f for f in sorted(cdir.iterdir()) if f.is_file() and not _is_junk(f)]
        names = []
        for f in files:
            rel = f"{sub}/{f.name}"
            if f.suffix.lower() not in spec.CHAT_EXTENSIONS:
                out.append(Finding(WARN, "파일", rel, "규격에 없는 파일 — 불필요 시 삭제"))
                continue
            if f.name != f.name.lower():
                out.append(Finding(FAIL, "파일명", rel, "파일명에 대문자 포함 — 모두 소문자"))
                continue
            if not _STEM_RE.match(f.stem):
                bad = sorted({ch for ch in f.stem if not re.match(r"[a-z0-9_]", ch)})
                out.append(Finding(FAIL, "파일명", rel,
                                   f"허용되지 않는 문자 {bad} 포함 — 영문 소문자/숫자/언더바만 가능"))
                continue
            names.append(f.name)

            size = spec.CHAT_SIZES[device][sub]
            actual = _image_size(f)
            if actual is None:
                out.append(Finding(FAIL, "크기", rel, "이미지를 열 수 없음 (손상/포맷 확인)"))
            elif actual != size:
                out.append(Finding(FAIL, "크기", rel,
                                   f"{actual[0]}×{actual[1]}px — 규격 {size[0]}×{size[1]}px"))
            else:
                out.append(Finding(PASS, "크기", rel, f"{size[0]}×{size[1]}px OK"))

            if f.suffix.lower() == ".gif":
                _check_gif_loop(f, rel, out)

        counts[sub] = sorted(names)

    if counts.get("large") is not None and counts.get("small") is not None:
        if counts["large"] != counts["small"]:
            only_l = set(counts["large"]) - set(counts["small"])
            only_s = set(counts["small"]) - set(counts["large"])
            out.append(Finding(WARN, "파일", "large/small",
                               "대화방 이미지 구성이 다름 — "
                               f"large에만: {sorted(only_l) or '없음'} / small에만: {sorted(only_s) or '없음'}"))
    if not any(counts.values()):
        out.append(Finding(PASS, "파일", "대화방", "대화방 이미지 없음 (선택 사항 — 통과)"))


def _check_gif_loop(f: Path, rel: str, out: List[Finding]) -> None:
    try:
        with Image.open(f) as im:
            loop = im.info.get("loop")
        if loop is None:
            out.append(Finding(WARN, "GIF", rel, "반복 횟수 정보 없음 (1회 재생) — 4회 규정 확인"))
        elif loop == 0:
            out.append(Finding(FAIL, "GIF", rel, "무한 반복으로 저장됨 — 4회 재생 후 멈춤 규정 위반"))
        elif loop in spec.GIF_LOOP_ALLOWED:
            out.append(Finding(PASS, "GIF", rel, f"반복 설정 OK (loop={loop})"))
        else:
            out.append(Finding(WARN, "GIF", rel,
                               f"반복 설정 loop={loop} — 규정(4회 재생)과 다를 수 있음"))
    except Exception as e:
        out.append(Finding(WARN, "GIF", rel, f"검사 실패: {e}"))


def _check_lowercase_all(device_dir: Path, out: List[Finding]) -> None:
    """전체 파일명 규칙: 모두 소문자 + 허용 문자(영문/숫자/언더바)만."""
    for f in device_dir.rglob("*"):
        if not f.is_file() or _is_junk(f):
            continue
        rel = f.relative_to(device_dir).as_posix()
        if f.name != f.name.lower():
            out.append(Finding(FAIL, "파일명", rel, "파일명에 대문자 포함 — 모두 소문자"))
        elif not _STEM_RE.match(f.stem):
            bad = sorted({ch for ch in f.stem if not re.match(r"[a-z0-9_]", ch)})
            out.append(Finding(FAIL, "파일명", rel,
                               f"허용되지 않는 문자 {bad} 포함 — 영문 소문자/숫자/언더바만 가능"))


def find_junk_files(device_dir: Path) -> List[Path]:
    """불필요 파일/폴더 목록 (삭제 후보)."""
    junk = []
    for f in device_dir.rglob("*"):
        if _is_junk(f):
            junk.append(f)
    return junk


def find_space_named(device_dir: Path) -> List[Path]:
    """이름(파일명·폴더명)에 공백이 포함된 항목 목록 (자동 정리 후보).

    깊은 경로부터 오도록 정렬 — rename_spaces_to_underscore() 가 하위 항목을 먼저
    바꿔야 상위 폴더 이름이 바뀌어도 나머지 경로가 깨지지 않는다.
    """
    items = [p for p in device_dir.rglob("*") if " " in p.name]
    return sorted(items, key=lambda p: len(p.parts), reverse=True)


def rename_spaces_to_underscore(device_dir: Path) -> List[Tuple[Path, Path]]:
    """이름에 공백이 있는 파일·폴더를 실제로 찾아 공백을 언더바(_)로 치환한다.

    find_space_named() 순서(깊은 경로 우선)대로 처리해, 상위 폴더명이 바뀌어도
    이미 처리된 하위 항목의 경로 문제가 생기지 않는다.
    반환: [(변경 전 경로, 변경 후 경로), ...]
    """
    renamed = []
    for p in find_space_named(device_dir):
        new_path = p.with_name(p.name.replace(" ", "_"))
        if new_path.exists():
            continue  # 이름 충돌 — 건너뛰고 수동 확인 필요
        p.rename(new_path)
        renamed.append((p, new_path))
    return renamed


def _check_junk_and_size(device_dir: Path, out: List[Finding]) -> None:
    for j in find_junk_files(device_dir):
        out.append(Finding(WARN, "불필요파일", str(j.relative_to(device_dir)),
                           "작업 잔재 파일 — 삭제 필요 ([불필요 파일 삭제] 버튼)"))

    total = sum(f.stat().st_size for f in device_dir.rglob("*") if f.is_file())
    mb = total / (1024 * 1024)
    if total > spec.TOTAL_SIZE_MAX:
        out.append(Finding(FAIL, "용량", device_dir.name,
                           f"전체 {mb:.2f}MB — 2MB 이내여야 함"))
    else:
        out.append(Finding(PASS, "용량", device_dir.name, f"전체 {mb:.2f}MB (≤2MB)"))


# ------------------------------------------------------------------ 진입점 --

class _NotifyList(list):
    """append 될 때마다 콜백을 불러주는 리스트 — 검수 진행 실시간 표시용."""

    def __init__(self, on_finding=None):
        super().__init__()
        self._on_finding = on_finding
        self._seen = set()

    def append(self, item):
        # 동일 지적(레벨·항목·대상·메시지) 중복 제거 —
        # 전용 검사(그룹/대화방 파일명)와 전체 파일명 스윕이 같은 파일을 겹쳐 잡는 경우 방지
        key = (item.level, item.category, item.target, item.message)
        if key in self._seen:
            return
        self._seen.add(key)
        super().append(item)
        if self._on_finding:
            self._on_finding(item)


def check_device_folder(folder, info: dict | None = None,
                        on_finding=None) -> List[Finding]:
    """디바이스 폴더('[MOBILE] happy' 등) 하나를 검수한다.

    info: {"name_ko": ..., "desc_ko": ..., "desc_en": ...} — GUI 입력(선택).
    on_finding: 검사 결과가 하나 나올 때마다 호출되는 콜백(Finding) — 진행 표시용.
    """
    device_dir = Path(folder)
    out: List[Finding] = _NotifyList(on_finding)

    parsed = parse_device_folder(device_dir)
    if not parsed:
        out.append(Finding(FAIL, "구조", device_dir.name,
                           "폴더명이 '[MOBILE] 영문명' / '[DESKTOP] 영문명' 형식이 아님"))
        return out
    device, en_name = parsed

    _check_info_texts(en_name, info or {}, out)
    _check_structure(device_dir, out)
    _check_group_files(device, en_name.lower(), device_dir, out)
    _check_chat_files(device, en_name.lower(), device_dir, out)
    _check_lowercase_all(device_dir, out)
    _check_junk_and_size(device_dir, out)
    return out


def summarize(findings: List[Finding]) -> Tuple[int, int, int]:
    """(PASS, WARN, FAIL) 건수."""
    return (sum(1 for f in findings if f.level == PASS),
            sum(1 for f in findings if f.level == WARN),
            sum(1 for f in findings if f.level == FAIL))
