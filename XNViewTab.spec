# -*- mode: python ; coding: utf-8 -*-
from pathlib import Path
root = Path(SPECPATH)
# Standard hooks include imported Qt modules, not every Qt/QML module.
a = Analysis(
    [str(root / 'src' / 'main.py')], pathex=[str(root)],
    binaries=[], datas=[(str(root / 'resources'), 'resources')],
    hiddenimports=[], hookspath=[], hooksconfig={}, runtime_hooks=[],
    excludes=[], noarchive=False, optimize=0,
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz, a.scripts, [], exclude_binaries=True, name='TABaTAB Cash',
    debug=False, bootloader_ignore_signals=False, strip=False, upx=False,
    console=False, disable_windowed_traceback=False,
    icon=str(root / 'resources' / 'app_icon.ico'),
    version=str(root / 'resources' / 'version_info.txt'),
)
coll = COLLECT(exe, a.binaries, a.datas, strip=False, upx=False, name='TABaTAB Cash')
