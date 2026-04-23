# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_data_files

textual_datas = collect_data_files('textual')
rich_datas = collect_data_files('rich')

a = Analysis(
    ['src/claude_session_manager/__main__.py'],
    pathex=['src'],
    binaries=[],
    datas=textual_datas + rich_datas,
    hiddenimports=[
        'claude_session_manager',
        'claude_session_manager.cli',
        'claude_session_manager.session_manager',
        'claude_session_manager.tui',
        'claude_session_manager.web_ui',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='claude-session-manager',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
    target_arch=None,
)
