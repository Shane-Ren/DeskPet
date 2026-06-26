import sys
import os
from pathlib import Path

block_cipher = None

project_root = Path(__file__).parent
assets_dir = project_root / "assets"
main_script = project_root / "main.py"
icon_path = assets_dir / "icon.ico"

a = Analysis(
    [str(main_script)],
    pathex=[str(project_root)],
    binaries=[],
    datas=[
        (str(assets_dir), "assets"),
    ],
    hiddenimports=[
        "PIL",
        "PIL.Image",
        "PIL.ImageTk",
        "pystray",
        "tkinter",
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="DesktopPet",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(icon_path) if icon_path.exists() else None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="DesktopPet",
)

# Single file build (alternative):
# pyinstaller --onefile --noconsole --add-data "assets;assets" --name DesktopPet main.py
