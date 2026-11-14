# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_all
import os
import shutil
from pathlib import Path

# Use the local Tcl/Tk runtime when building in a restricted environment.
tcl_runtime = Path(SPECPATH) / '.build-deps' / 'tcl-runtime'
if tcl_runtime.is_dir():
    os.environ['TCL_LIBRARY'] = str(tcl_runtime / 'tcl8.6')
    os.environ['TK_LIBRARY'] = str(tcl_runtime / 'tk8.6')

from PyInstaller.utils.hooks.tcl_tk import tcltk_info
if not tcltk_info.available:
    raise RuntimeError('Tcl/Tk unavailable: refusing to build an app without tkinter')

datas = []
binaries = []
hiddenimports = []
tmp_ret = collect_all('windows_capture')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]


a = Analysis(
    ['app.py'],
    pathex=['.capture-deps'],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['matplotlib', 'scipy', 'pandas'],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='AutoE7',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='AutoE7',
)

# App data is intentionally external, beside the EXE. PyInstaller 6 places
# COLLECT DATA entries under _internal by default, unlike app.py's ROOT.
portable_root = Path(coll.name)
shutil.copytree(Path(SPECPATH) / 'assets', portable_root / 'assets', dirs_exist_ok=True)
for filename in ('scenarios.json', 'release_config.json', 'PORTABLE-GUIDE.txt',
                 'README.md', 'README.en.md', 'RELEASING.md'):
    shutil.copy2(Path(SPECPATH) / filename, portable_root / filename)
