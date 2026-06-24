import threading
import queue
import time
import tkinter as tk
from PIL import Image, ImageTk

_doll_queue: queue.Queue = None
_active_windows = []


def _init_queue(q: queue.Queue):
    global _doll_queue
    _doll_queue = q


def run_doll(gif_path: str, duration_sec: float, settings: dict):
    """在独立线程中运行一个玩偶窗口"""
    t = threading.Thread(target=_doll_thread, args=(gif_path, duration_sec, settings), daemon=True)
    t.start()


def _load_gif_frames(gif_path: str, target_size: int) -> list:
    """用 PIL 加载 GIF 每一帧，缩放到 target_size，白色背景，完美透明"""
    frames = []
    try:
        gif = Image.open(gif_path)
        while True:
            frame = gif.copy().convert("RGBA")
            if frame.size != (target_size, target_size):
                frame = frame.resize((target_size, target_size), Image.LANCZOS)
            bg = Image.new("RGBA", frame.size, (255, 255, 255, 255))
            composite = Image.alpha_composite(bg, frame)
            tk_img = ImageTk.PhotoImage(composite.convert("RGB"))
            frames.append(tk_img)
            gif.seek(gif.tell() + 1)
    except EOFError:
        pass
    return frames


def _doll_thread(gif_path: str, duration_sec: float, settings: dict):
    _doll_queue.put((gif_path, duration_sec, settings))


def process_doll_queue(root: tk.Tk):
    """在主线程的 Tk 事件循环中调用，不断检查队列并创建 doll 窗口"""
    while True:
        try:
            gif_path, duration_sec, settings = _doll_queue.get_nowait()
            _create_doll_window(root, gif_path, duration_sec, settings)
        except queue.Empty:
            break
    root.after(100, process_doll_queue, root)


def _create_doll_window(root: tk.Tk, gif_path: str, duration_sec: float, settings: dict):
    size = settings.get("window_size_px", 128)
    speed = settings.get("speed", 10)
    travel_distance = settings.get("travel_distance", 500)
    is_topmost = settings.get("is_always_on_top", True)
    bottom_margin = settings.get("bottom_margin", 45)

    frames = _load_gif_frames(gif_path, size)
    if not frames:
        return

    doll = tk.Toplevel(root)
    doll.wm_attributes("-transparentcolor", "white")
    doll.overrideredirect(True)
    if is_topmost:
        doll.attributes("-topmost", True)

    label = tk.Label(doll, bd=0, highlightthickness=0, bg="white")
    label.pack()
    label.configure(image=frames[0])

    # 使用负坐标语法 -x-y，直接锚定屏幕右下角
    # -x 表示距右边缘距离，-y 表示距底部距离
    x_offset = [0]  # 距右边缘的偏移
    direction = [1]  # 1=向左移(offset增大)，-1=向右移(offset减小)

    frame_index = [0]
    timestamp = [time.time()]

    def update():
        if time.time() > timestamp[0] + 0.06:
            timestamp[0] = time.time()
            frame_index[0] = (frame_index[0] + 1) % len(frames)

        x_offset[0] += direction[0]
        if x_offset[0] >= travel_distance:
            x_offset[0] = travel_distance
            direction[0] = -1
        elif x_offset[0] <= 0:
            x_offset[0] = 0
            direction[0] = 1

        label.configure(image=frames[frame_index[0]])
        # -x-y 语法：距右边缘 x_offset，距底部 bottom_margin
        doll.geometry(f"{size}x{size}-{x_offset[0]}-{bottom_margin}")
        doll.after(speed, update)

    # 初始位置：紧贴右下角
    doll.geometry(f"{size}x{size}-0-{bottom_margin}")
    doll.after(0, update)
    _active_windows.append(doll)

    def cleanup():
        if doll in _active_windows:
            _active_windows.remove(doll)

    doll.after(int(duration_sec * 1000), doll.destroy)
    doll.after(int(duration_sec * 1000) + 100, cleanup)
