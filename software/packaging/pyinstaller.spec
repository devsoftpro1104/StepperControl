# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec для controller_app.

block_cipher = None

a = Analysis(
    ['../src/controller_app/__main__.py'],
    pathex=['../src'],
    binaries=[],
    datas=[
        ('../resources', 'resources'),
    ],
    hiddenimports=['PyQt6', 'pyqtgraph', 'serial'],
    hookspath=[],
    runtime_hooks=[],
    excludes=[],
    cipher=block_cipher,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)
exe = EXE(
    pyz, a.scripts, [],
    exclude_binaries=True,
    name='controller_app',
    console=False,
)
coll = COLLECT(exe, a.binaries, a.zipfiles, a.datas, name='controller_app')