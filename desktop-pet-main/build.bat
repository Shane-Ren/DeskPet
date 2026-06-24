@echo off
echo Building DesktopPet.exe...
pip install pyinstaller pystray Pillow -q
pyinstaller --onefile --noconsole --add-data "assets;assets" --name DesktopPet --icon assets/icon.ico main.py
echo Done! EXE is in dist/DesktopPet.exe
pause
