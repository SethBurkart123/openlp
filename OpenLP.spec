# -*- mode: python ; coding: utf-8 -*-

import os
import sys
from pathlib import Path


ROOT_PATH = Path(__file__).resolve().parent
BUILD_TARGET = os.environ.get('OPENLP_BUILD_TARGET', sys.platform)
SCRIPT_PATH = str(ROOT_PATH / 'openlp' / '__main__.py')
HOOK_PATH = str(ROOT_PATH / 'packaging' / 'pyinstaller-hooks')
RUNTIME_HOOK_PATH = str(Path(HOOK_PATH) / 'rthook_ssl.py')
WINDOWS_ICON_PATH = str(ROOT_PATH / 'packaging' / 'windows' / 'OpenLP.ico')
MACOS_ICON_PATH = str(ROOT_PATH / 'packaging' / 'macos' / 'OpenLP.icns')


a = Analysis(
    [SCRIPT_PATH],
    pathex=[],
    binaries=[],
    datas=[],
    hiddenimports=['sqlalchemy.ext.baked'],
    hookspath=[HOOK_PATH],
    hooksconfig={},
    runtime_hooks=[RUNTIME_HOOK_PATH],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='OpenLP',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=[WINDOWS_ICON_PATH],
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name='OpenLP',
)

if BUILD_TARGET in {'darwin', 'macos'}:
    app = BUNDLE(
        coll,
        name='OpenLP.app',
        icon=MACOS_ICON_PATH,
        bundle_identifier=None,
    )
