# -*- mode: python ; coding: utf-8 -*-
# PyInstaller 빌드 스펙 — build.bat 이 이 파일을 사용한다.
#   빌드: pyinstaller emoticon_checker.spec
#   결과: dist/emoticon_checker_v{버전}.exe (단일 파일, 콘솔창 없음)
#
#   파일명에 emoticon_checker.py 의 APP_VERSION 을 자동으로 붙인다 — 재빌드할 때마다
#   기존 exe(예: emoticon_checker.exe, emoticon_checker_v0.2.0.exe)를 덮어쓰지 않고
#   새 버전 파일로 나란히 남겨서, "구버전 exe를 최신인 줄 알고 테스트"하는 혼란을 막는다.
#   버전을 올리려면 emoticon_checker.py 의 APP_VERSION 만 수정하면 된다.

import re
import sys
from pathlib import Path

python_root = Path(sys.base_prefix)
tcl_root = python_root / 'tcl'
dll_root = python_root / 'DLLs'
lib_root = python_root / 'Lib'

_src = Path('emoticon_checker.py').read_text(encoding='utf-8')
_m = re.search(r'APP_VERSION\s*=\s*"([^"]+)"', _src)
APP_VERSION = _m.group(1) if _m else 'unknown'

a = Analysis(
    ['emoticon_checker.py'],
    pathex=[],
    binaries=[
        (str(dll_root / '_tkinter.pyd'), '.'),
        (str(dll_root / 'tcl86t.dll'), '.'),
        (str(dll_root / 'tk86t.dll'), '.'),
    ],
    datas=[
        ('assets', 'assets'),
        (str(lib_root / 'tkinter'), 'tkinter'),
        (str(tcl_root / 'tcl8.6'), '_tcl_data'),
        (str(tcl_root / 'tk8.6'), '_tk_data'),
    ],
    hiddenimports=['_tkinter'],
    runtime_hooks=['pyi_rth_tkinter_custom.py'],
    excludes=[],
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name=f'emoticon_checker_v{APP_VERSION}',
    debug=False,
    strip=False,
    upx=False,
    console=False,          # GUI 앱 — 콘솔창 숨김
    # icon='assets/icon.ico',  # 아이콘 준비되면 주석 해제
)
