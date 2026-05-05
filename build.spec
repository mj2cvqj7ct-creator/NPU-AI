# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec file for NPU Audio Enhancer.
Build with: pyinstaller build.spec

PyInstaller executes the spec without defining __file__; use SPECPATH (spec dir).
"""

import os
import sys
from pathlib import Path

from PyInstaller.utils.hooks import (
    collect_data_files,
    collect_dynamic_libs,
    collect_submodules,
)

# SPECPATH is set by PyInstaller to the directory containing this spec file.
_REPO_ROOT = Path(os.path.abspath(SPECPATH))
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))


def _safe_collect(fn, name):
    """Run a PyInstaller collector, returning [] if the package isn't installed.

    This lets the spec be valid on dev machines that don't have every
    Windows-only dependency installed.
    """
    try:
        return fn(name)
    except Exception as exc:  # noqa: BLE001
        print(f"build.spec: {fn.__name__}('{name}') skipped: {exc}")
        return []


# winsdk is a dynamic WinRT projection — its submodules are generated at
# runtime from .winmd files, so PyInstaller's static graph misses them.
# We need to collect:
#   - all submodules (winsdk.windows.*) so importlib.import_module() works
#   - the bundled .winmd / native projection .pyd helper files (data files)
#   - the actual native .dll dependencies (dynamic libs)
# Without these the SMTC bridge always fails on Snapdragon X and the UI
# stays stuck on "システム音 待機中".
_WINSDK_HIDDEN = _safe_collect(collect_submodules, "winsdk")
_WINSDK_DATAS = _safe_collect(collect_data_files, "winsdk")
_WINSDK_BINS = _safe_collect(collect_dynamic_libs, "winsdk")
_ONNX_QNN_HIDDEN = _safe_collect(collect_submodules, "onnxruntime")
_ONNX_QNN_DATAS = _safe_collect(collect_data_files, "onnxruntime")
_ONNX_QNN_BINS = _safe_collect(collect_dynamic_libs, "onnxruntime")
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

_MAIN = str(_REPO_ROOT / "src" / "main.py")
_APP_ICO = _REPO_ROOT / "resources" / "icons" / "app.ico"
_exe_icon_kw = {}
if _APP_ICO.is_file():
    _exe_icon_kw = {"icon": str(_APP_ICO)}

a = Analysis(
    [_MAIN],
    pathex=[str(_REPO_ROOT)],
    binaries=[*_WINSDK_BINS, *_ONNX_QNN_BINS],
    datas=[
        ('resources', 'resources'),
        ('models', 'models'),
        *_WINSDK_DATAS,
        *_ONNX_QNN_DATAS,
    ],
    hiddenimports=[
        'PyQt6',
        'PyQt6.QtCore',
        'PyQt6.QtGui',
        'PyQt6.QtWidgets',
        'numpy',
        # numpy.testing is imported transitively by scipy._lib._array_api at
        # module load time. PyInstaller does not always pick this up via the
        # static graph, so list it explicitly.
        'numpy.testing',
        'scipy',
        'scipy.signal',
        'scipy.fft',
        'scipy.spatial',
        'scipy.sparse',
        'scipy._lib._array_api',
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
        # Streaming detector dependencies — winsdk preferred, winrt fallback.
        'winsdk',
        'winsdk.windows.media.control',
        'winsdk.windows.foundation',
        *_WINSDK_HIDDEN,
        *_ONNX_QNN_HIDDEN,
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'matplotlib',
        'tkinter',
        # NOTE: do NOT exclude 'unittest' — scipy>=1.12 loads numpy.testing
        # transitively at import time (scipy.spatial → scipy.sparse →
        # scipy._lib._array_api → numpy.testing), and numpy.testing requires
        # unittest. Excluding it makes the frozen EXE crash on launch with
        # "ModuleNotFoundError: No module named 'unittest'".
        'test',
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
    **_exe_icon_kw,
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
