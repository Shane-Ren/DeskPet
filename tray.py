import os
import sys
import threading
import webbrowser
from pathlib import Path

import pystray
from PIL import Image

import config_manager

APP_NAME = "DesktopPet"
KEY_PATH = r"Software\Microsoft\Windows\CurrentVersion\Run"

_tray_icon = [None]
_on_show_panel = [None]
_on_quit = [None]


def _get_icon_path() -> str:
    if getattr(sys, "frozen", False):
        base = Path(sys._MEIPASS)
    else:
        base = Path(os.path.dirname(os.path.abspath(__file__)))
    return str(base / "assets" / "tray-icon.png")


def _get_exe_path() -> str:
    if getattr(sys, "frozen", False):
        return sys.executable
    return os.path.abspath(sys.executable)


def is_auto_start() -> bool:
    try:
        import winreg

        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, KEY_PATH, 0, winreg.KEY_READ)
        winreg.QueryValueEx(key, APP_NAME)
        winreg.CloseKey(key)
        return True
    except FileNotFoundError:
        return False
    except Exception:
        return False


def enable_auto_start():
    try:
        import winreg

        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, KEY_PATH, 0, winreg.KEY_SET_VALUE)
        winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_SZ, _get_exe_path())
        winreg.CloseKey(key)
    except Exception:
        pass


def disable_auto_start():
    try:
        import winreg

        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, KEY_PATH, 0, winreg.KEY_SET_VALUE)
        winreg.DeleteValue(key, APP_NAME)
        winreg.CloseKey(key)
    except FileNotFoundError:
        pass
    except Exception:
        pass


def _toggle_auto_start(icon, item):
    if is_auto_start():
        disable_auto_start()
    else:
        enable_auto_start()
    _refresh_menu(icon)


def _refresh_menu(icon):
    menu = pystray.Menu(
        pystray.MenuItem("打开控制面板", _on_show_panel[0], default=True),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem(
            "开机自启",
            _toggle_auto_start,
            checked=lambda i: is_auto_start(),
        ),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("退出", _on_quit[0]),
    )
    icon.menu = menu


def _show_panel(icon):
    if _on_show_panel[0]:
        _on_show_panel[0](icon)


def _quit_app(icon):
    if _on_quit[0]:
        _on_quit[0]()
    icon.stop()


def run_tray(on_show_panel, on_quit):
    _on_show_panel[0] = on_show_panel
    _on_quit[0] = on_quit

    icon_image = Image.open(_get_icon_path())
    menu = pystray.Menu(
        pystray.MenuItem("打开控制面板", _show_panel, default=True),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem(
            "开机自启",
            _toggle_auto_start,
            checked=lambda i: is_auto_start(),
        ),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("退出", _quit_app),
    )

    icon = pystray.Icon(APP_NAME, icon_image, "Desktop Pet", menu)
    _tray_icon[0] = icon
    icon.run_detached()
