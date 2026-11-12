# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller build for CONVERTOR-APP (v0.6.1).

One Windows .exe, no console window: double-click and the GUI
opens. Run locally on Windows with:
    pip install -r requirements.txt
    pip install pyinstaller
    pyinstaller --clean --noconfirm CONVERTOR-APP.spec
The GitHub Actions workflow (.github/workflows/build-exe.yml)
runs exactly this file, so the Release .exe matches a local build.

No data files are bundled: the icon is drawn in code, settings
live in the user's home folder (~/.convertor-app), and there are
no .ui/.qrc/image files. The hidden imports below are the
third-party packages imported lazily inside functions
(markdown, python-docx, PyMuPDF, reportlab) — listed explicitly
so the frozen app never misses one.
"""

block_cipher = None

a = Analysis(
    ["main.py"],
    pathex=[],
    binaries=[],
    datas=[],
    hiddenimports=[
        "markdown",
        "docx",
        "pymupdf",
        "fitz",
        "reportlab",
        "reportlab.lib.pagesizes",
        "reportlab.lib.styles",
        "reportlab.lib.units",
        "reportlab.platypus",
        "PIL",
    ],
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
    [],
    name="CONVERTOR-APP",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
