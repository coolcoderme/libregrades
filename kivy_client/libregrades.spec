# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_all
from kivy_deps import sdl2, glew
import sys
from pathlib import Path

block_cipher = None
root = Path(SPECPATH)

datas = [(str(root / 'libregrades.kv'), '.')]
hiddenimports = ['requests', 'libregrades_sdk']

a = Analysis(
    [str(root / 'main.py')],
    pathex=[str(root), str(root.parent / 'shared')],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    *[Tree(p) for p in (sdl2.dep_bins + glew.dep_bins)],
    name='LibreGrades',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,
)
