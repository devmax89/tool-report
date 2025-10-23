# app.spec
# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_submodules, collect_data_files
import sys

block_cipher = None

# Raccogli tutti i submodules necessari
hiddenimports = []
hiddenimports += collect_submodules('numpy')
hiddenimports += collect_submodules('pandas')
hiddenimports += collect_submodules('flask_socketio')
hiddenimports += collect_submodules('socketio')
hiddenimports += collect_submodules('engineio')

# MongoDB e SSH dependencies
hiddenimports += collect_submodules('pymongo')
hiddenimports += collect_submodules('sshtunnel')
hiddenimports += collect_submodules('paramiko')
hiddenimports += collect_submodules('cryptography')

# Moduli custom
hiddenimports += [
    'email_service', 
    'monitoring_service', 
    'digil_test_service',
    'mongodb_checker',
    'dotenv', 
    'jinja2'
]

# Raccogli i data files
datas = []
datas += collect_data_files('numpy')
datas += collect_data_files('pandas')
datas += collect_data_files('flask_socketio')
datas += collect_data_files('socketio')
datas += collect_data_files('engineio')

# Data files per MongoDB
datas += collect_data_files('pymongo')
datas += collect_data_files('cryptography')

# Files del progetto
datas += [
    ('templates', 'templates'),
    ('templates_excel', 'templates_excel'),
    ('static', 'static'),
    ('email_service.py', '.'),
    ('monitoring_service.py', '.'),
    ('digil_test_service.py', '.'),
    ('mongodb_checker.py', '.'),  # 🆕 NUOVO
    ('config', 'config'),
]

# Aggiungi .env se esiste
import os
if os.path.exists('.env'):
    datas.append(('.env', '.'))

a = Analysis(
    ['app.py'],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['matplotlib', 'scipy', 'tkinter'],
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
    name='DIGIL_Report_Generator',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=True,
    disable_windowed_traceback=False,
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
    upx=False,
    upx_exclude=[],
    name='DIGIL_Report_Generator',
)