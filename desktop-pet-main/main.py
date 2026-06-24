import platform
import ctypes
import queue
import sys

# 开启 Windows 高 DPI 感知，获取真实物理像素坐标
if platform.system() == "Windows":
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        pass

import tkinter as tk

import config_manager
import control_panel
import doll_window
import scheduler
import tray


def main():
    config_manager.ensure_default_materials()
    scheduler.get_scheduler().start_all()

    root = tk.Tk()
    # 移到屏幕外，不 withdraw（Toplevel 子窗口需要父窗口可见才能正确透明）
    root.geometry("1x1+10000+10000")
    root.attributes("-alpha", 0)

    q = queue.Queue()
    doll_window._init_queue(q)
    doll_window.process_doll_queue(root)

    panel = control_panel.ControlPanel(root)

    tray.run_tray(
        on_show_panel=lambda _: panel.show(),
        on_quit=lambda: _quit(root),
    )

    panel.show()
    root.mainloop()


def _quit(root):
    scheduler.get_scheduler().stop_all()
    root.quit()
    sys.exit(0)


if __name__ == "__main__":
    main()
