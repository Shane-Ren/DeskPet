import threading
import config_manager
import doll_window


class TaskScheduler:
    def __init__(self):
        self._timers: dict[str, threading.Timer] = {}
        self._lock = threading.Lock()

    def _fire_task(self, task_id: str):
        task = config_manager.get_task(task_id)
        if task and task.get("enabled"):
            gif_path = config_manager.get_material_path(task["gif_id"])
            if gif_path:
                settings = config_manager.get_pet_settings()
                doll_window.run_doll(gif_path, task["duration_seconds"], settings)
        self._reschedule(task_id)

    def _reschedule(self, task_id: str):
        with self._lock:
            task = config_manager.get_task(task_id)
            if not task or not task.get("enabled"):
                return
            interval = task["interval_minutes"] * 60
            timer = threading.Timer(interval, self._fire_task, args=(task_id,))
            self._timers[task_id] = timer
            timer.start()

    def start_task(self, task_id: str):
        self.stop_task(task_id)
        self._reschedule(task_id)

    def stop_task(self, task_id: str):
        with self._lock:
            if task_id in self._timers:
                self._timers[task_id].cancel()
                del self._timers[task_id]

    def start_all(self):
        for task in config_manager.get_all_tasks():
            if task.get("enabled"):
                self.start_task(task["id"])

    def stop_all(self):
        with self._lock:
            for t in self._timers.values():
                t.cancel()
            self._timers.clear()

    def restart_task(self, task_id: str):
        self.stop_task(task_id)
        task = config_manager.get_task(task_id)
        if task and task.get("enabled"):
            self.start_task(task_id)

    def trigger_now(self, task_id: str):
        task = config_manager.get_task(task_id)
        if task:
            gif_path = config_manager.get_material_path(task["gif_id"])
            if gif_path:
                settings = config_manager.get_pet_settings()
                doll_window.run_doll(gif_path, task["duration_seconds"], settings)


_scheduler = TaskScheduler()


def get_scheduler() -> TaskScheduler:
    return _scheduler
