# -*- mode: python ; coding: utf-8 -*-
import os
import flet
import flet_web

block_cipher = None

flet_dir = os.path.dirname(flet.__file__)
flet_web_dir = os.path.dirname(flet_web.__file__)

flet_web_assets = os.path.join(flet_web_dir, "web")
flet_icons_json = os.path.join(flet_dir, "controls", "material", "icons.json")

added_files = [
    ('src', 'src'),
    ('src/assets', 'assets'),
    (flet_web_assets, 'flet_web/web'),
    (flet_icons_json, 'flet/controls/material'),
]

a = Analysis(
    ['src/main.py'],
    pathex=['src'],
    binaries=[],
    datas=added_files,
    hiddenimports=[
        'sqlite3',
        'aiosqlite',
        'greenlet',
        'sqlalchemy.sql.functions',
        'sqlalchemy.ext.asyncio',
        'psycopg2',
        'asyncpg',
        'flet_web',
        'uvicorn.logging',
        'uvicorn.loops',
        'uvicorn.loops.auto',
        'uvicorn.protocols',
        'uvicorn.protocols.http',
        'uvicorn.protocols.http.auto',
        'uvicorn.protocols.websockets',
        'uvicorn.protocols.websockets.auto',
        'uvicorn.lifespan',
        'uvicorn.lifespan.on',
        'flet.utils.once'
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
    [],
    exclude_binaries=True,
    name='SpotipyDashboard',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True, 
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='SpotipyDashboard',
)
