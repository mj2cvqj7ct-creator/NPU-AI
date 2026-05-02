# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec file for NPU Audio Enhancer.
Build with: pyinstaller build.spec
"""

import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))
_models_dir = _REPO_ROOT / "models"
_models_dir.mkdir(parents=True, exist_ok=True)
try:
    from src.npu.models import ensure_models_exist

    ensure_models_exist(str(_models_dir))
except Exception as exc:
    print(
        f"Warning: ONNX placeholder refresh failed ({exc}); "
        "run the app once with onnx installed to populate ./models",
    )

block_cipher = None

a = Analysis(
    ['src/main.py'],
    pathex=['.'],
    binaries=[],
    datas=[
        ('resources', 'resources'),
        ('models', 'models'),
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
        'onnx',
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
