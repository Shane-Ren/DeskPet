@echo off
echo Installing dependencies...
pip install pyinstaller pystray Pillow tkinterdnd2 -q
echo Building DesktopPet.exe...
pyinstaller --onefile --noconsole ^
  --add-data "assets;assets" ^
  --name DesktopPet ^
  --icon assets/icon.ico ^
  --distpath dist ^
  main.py
echo Done! EXE is at dist/DesktopPet.exe
pause
