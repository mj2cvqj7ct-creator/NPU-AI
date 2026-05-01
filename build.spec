# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec file for NPU Audio Enhancer.
Build with: pyinstaller build.spec
"""

import sys
from pathlib import Path

block_cipher = None

a = Analysis(
    ['src/main.py'],
    pathex=['.'],
    binaries=[],
    datas=[
        ('resources', 'resources'),
    ],
    hiddenimports=[
        'PyQt6',
        'PyQt6.QtCore',
        'PyQt6.QtGui',
        'PyQt6.QtWidgets',
        'numpy',
        'scipy',
        'scipy.signal',
        'scipy.fft',
        'scipy.spatial',
        'sounddevice',
        'onnxruntime',
        'librosa',
        'sklearn',
        'psutil',
        'comtypes',
        'pycaw',
        'pycaw.pycaw',
        'yaml',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'matplotlib',
        'tkinter',
        'test',
        'unittest',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='NPU_Audio_Enhancer',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch='arm64',
    icon='resources/icons/app.ico',
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='NPU_Audio_Enhancer',
)
