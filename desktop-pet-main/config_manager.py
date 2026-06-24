import json
import os
import shutil
import threading
import uuid
from pathlib import Path

CONFIG_DIR = Path(os.environ["APPDATA"]) / "desktop-pet"
CONFIG_FILE = CONFIG_DIR / "config.json"
MEDIA_DIR = CONFIG_DIR / "media"
ASSETS_DIR = Path(os.path.dirname(os.path.abspath(__file__))) / "assets"
_lock = threading.Lock()


def resource_path(relative_path: str) -> Path:
    if getattr(sys, "frozen", False):
        base = Path(sys._MEIPASS)
    else:
        base = Path(os.path.dirname(os.path.abspath(__file__)))
    return base / relative_path


import sys

DEFAULT_CONFIG = {
    "version": 1,
    "pet_settings": {
        "dock_edge": "bottom-right",
        "travel_distance": 500,
        "speed": 10,
        "is_always_on_top": True,
        "window_size_px": 128,
        "bottom_margin": 45,
    },
    "tasks": [],
    "materials": [],
    "system": {
        "auto_start": False,
    },
}


def _default_config() -> dict:
    return json.loads(json.dumps(DEFAULT_CONFIG))


def load() -> dict:
    if CONFIG_FILE.exists():
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return _default_config()


def save(cfg: dict):
    with _lock:
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(cfg, f, ensure_ascii=False, indent=2)


def get_materials_dir() -> Path:
    MEDIA_DIR.mkdir(parents=True, exist_ok=True)
    return MEDIA_DIR


def ensure_default_materials():
    """首次运行将 assets 目录下的 gif 复制到 media 目录作为默认素材"""
    cfg = load()
    if cfg["materials"]:
        return
    default_gifs = list(ASSETS_DIR.glob("*.gif"))
    for gif_path in default_gifs:
        add_material(str(gif_path), gif_path.stem, "默认")


def add_material(src_path: str, name: str, category: str) -> dict:
    mat_id = str(uuid.uuid4())[:8]
    dest = get_materials_dir() / f"{mat_id}.gif"
    shutil.copy2(src_path, dest)
    mat = {"id": mat_id, "name": name, "category": category, "filename": f"{mat_id}.gif"}
    cfg = load()
    cfg["materials"].append(mat)
    save(cfg)
    return mat


def remove_material(mat_id: str):
    cfg = load()
    cfg["materials"] = [m for m in cfg["materials"] if m["id"] != mat_id]
    save(cfg)
    mat_file = get_materials_dir() / f"{mat_id}.gif"
    if mat_file.exists():
        mat_file.unlink()


def get_material_path(mat_id: str) -> str | None:
    cfg = load()
    for m in cfg["materials"]:
        if m["id"] == mat_id:
            return str(get_materials_dir() / m["filename"])
    return None


def get_all_materials() -> list[dict]:
    return load().get("materials", [])


def get_task(task_id: str) -> dict | None:
    cfg = load()
    for t in cfg["tasks"]:
        if t["id"] == task_id:
            return t
    return None


def get_all_tasks() -> list[dict]:
    return load().get("tasks", [])


def save_task(task: dict):
    cfg = load()
    for i, t in enumerate(cfg["tasks"]):
        if t["id"] == task["id"]:
            cfg["tasks"][i] = task
            save(cfg)
            return
    cfg["tasks"].append(task)
    save(cfg)


def delete_task(task_id: str):
    cfg = load()
    cfg["tasks"] = [t for t in cfg["tasks"] if t["id"] != task_id]
    save(cfg)


def get_pet_settings() -> dict:
    return load().get("pet_settings", DEFAULT_CONFIG["pet_settings"])


def save_pet_settings(settings: dict):
    cfg = load()
    cfg["pet_settings"] = settings
    save(cfg)


def get_system_settings() -> dict:
    return load().get("system", DEFAULT_CONFIG["system"])


def save_system_settings(sys_settings: dict):
    cfg = load()
    cfg["system"] = sys_settings
    save(cfg)
