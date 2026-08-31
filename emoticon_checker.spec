# -*- mode: python ; coding: utf-8 -*-
# PyInstaller 빌드 스펙 — build.bat 이 이 파일을 사용한다.
#   빌드: pyinstaller emoticon_checker.spec
#   결과: dist/emoticon_checker_v03.exe (단일 파일, 콘솔창 없음)

import sys
from pathlib import Path

python_root = Path(sys.base_prefix)
tcl_root = python_root / 'tcl'
dll_root = python_root / 'DLLs'
lib_root = python_root / 'Lib'

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
    name='emoticon_checker_v03',
    debug=False,
    strip=False,
    upx=False,
    console=False,          # GUI 앱 — 콘솔창 숨김
    # icon='assets/icon.ico',  # 아이콘 준비되면 주석 해제
)
