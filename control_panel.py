import ctypes
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import uuid
from pathlib import Path

import config_manager
import scheduler


class ScrollFrame(ttk.Frame):
    def __init__(self, parent, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)
        canvas = tk.Canvas(self, borderwidth=0, highlightthickness=0)
        scrollbar = ttk.Scrollbar(self, orient="vertical", command=canvas.yview)
        self.interior = ttk.Frame(canvas)
        self.interior.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=self.interior, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        canvas.bind_all("<MouseWheel>", _on_mousewheel)
        self._canvas = canvas

    def destroy(self):
        try:
            self._canvas.bind_all("<MouseWheel>", lambda e: None)
        except Exception:
            pass
        super().destroy()


class ControlPanel:
    def __init__(self, root, on_close=None):
        self._on_close = on_close
        self._materials = []
        self._tasks = []
        self._selected_mat_id = None

        self._root = tk.Toplevel(root)
        self._root.title("Desktop Pet - 控制面板")
        self._root.geometry("650x560")
        self._root.minsize(500, 450)
        self._root.protocol("WM_DELETE_WINDOW", self._on_window_close)
        # 创建后立即隐藏任务栏图标（WS_EX_TOOLWINDOW）
        self._root.update_idletasks()
        try:
            GWL_EXSTYLE = -20
            WS_EX_TOOLWINDOW = 0x00000080
            hwnd = self._root.winfo_id()
            style = ctypes.windll.user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
            ctypes.windll.user32.SetWindowLongW(hwnd, GWL_EXSTYLE, style | WS_EX_TOOLWINDOW)
        except Exception:
            pass

        nb = ttk.Notebook(self._root)
        nb.pack(fill="both", expand=True, padx=8, pady=8)

        self._materials_frame = ttk.Frame(nb)
        self._tasks_frame = ttk.Frame(nb)
        self._settings_scroll = ScrollFrame(nb)

        nb.add(self._materials_frame, text="素材管理")
        nb.add(self._settings_scroll, text="桌宠设置")
        nb.add(self._tasks_frame, text="定时任务")

        self._build_materials_tab()
        self._build_tasks_tab()
        self._build_settings_tab()

        self._refresh_materials()
        self._refresh_tasks()

    def _on_window_close(self):
        self._root.withdraw()

    def show(self):
        self._root.deiconify()
        self._root.lift()
        self._root.focus_force()

    # ─── 素材管理 ───────────────────────────────────────────

    def _build_materials_tab(self):
        f = self._materials_frame

        toolbar = ttk.Frame(f)
        toolbar.pack(fill="x", padx=8, pady=(8, 4))
        ttk.Button(toolbar, text="上传 GIF", command=self._upload_material).pack(side="left")
        ttk.Button(toolbar, text="删除选中", command=self._delete_material).pack(side="left", padx=4)

        list_frame = ttk.Frame(f)
        list_frame.pack(fill="both", expand=True, padx=8, pady=4)

        cols = ("name", "category")
        self._mat_tree = ttk.Treeview(list_frame, columns=cols, show="headings")
        self._mat_tree.heading("name", text="名称")
        self._mat_tree.heading("category", text="分类")
        self._mat_tree.column("name", width=200)
        self._mat_tree.column("category", width=150)
        scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=self._mat_tree.yview)
        self._mat_tree.configure(yscrollcommand=scrollbar.set)
        self._mat_tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        self._mat_tree.bind("<<TreeviewSelect>>", self._on_mat_select)

        preview_frame = ttk.LabelFrame(f, text="预览", padding=8)
        preview_frame.pack(fill="x", padx=8, pady=(4, 8))
        self._preview_lbl = ttk.Label(preview_frame, text="选择素材可预览")
        self._preview_lbl.pack()

    def _upload_material(self):
        path = filedialog.askopenfilename(filetypes=[("GIF 图片", "*.gif")])
        if not path:
            return
        dialog = _NewMaterialDialog(self._root, path)
        if dialog.result:
            name, category = dialog.result
            config_manager.add_material(path, name, category)
            self._refresh_materials()

    def _delete_material(self):
        sel = self._mat_tree.selection()
        if not sel:
            return
        if messagebox.askyesno("确认", "确定删除该素材？"):
            item = self._mat_tree.item(sel[0])["values"]
            mat_name = item[0]
            for m in config_manager.get_all_materials():
                if m["name"] == mat_name:
                    config_manager.remove_material(m["id"])
                    break
            self._refresh_materials()

    def _on_mat_select(self, _):
        sel = self._mat_tree.selection()
        if not sel:
            self._selected_mat_id = None
            self._preview_lbl.configure(image="", text="选择素材可预览")
            return
        item = self._mat_tree.item(sel[0])["values"]
        mat_name = item[0]
        for m in config_manager.get_all_materials():
            if m["name"] == mat_name:
                self._selected_mat_id = m["id"]
                self._show_preview(m["id"])
                break

    def _show_preview(self, mat_id):
        path = config_manager.get_material_path(mat_id)
        if not path:
            self._preview_lbl.configure(image="", text="素材不存在")
            return
        try:
            from PIL import Image, ImageTk
            img = Image.open(path)
            img.thumbnail((120, 120))
            ph = ImageTk.PhotoImage(img)
            self._preview_lbl.configure(image=ph, text="")
            self._preview_lbl.image = ph
        except Exception as e:
            self._preview_lbl.configure(image="", text=f"预览失败: {e}")

    def _refresh_materials(self):
        self._mat_tree.delete(*self._mat_tree.get_children())
        self._materials = config_manager.get_all_materials()
        for m in self._materials:
            self._mat_tree.insert("", "end", values=(m["name"], m["category"]))

    # ─── 定时任务 ───────────────────────────────────────────

    def _build_tasks_tab(self):
        f = self._tasks_frame

        toolbar = ttk.Frame(f)
        toolbar.pack(fill="x", padx=8, pady=(8, 4))
        ttk.Button(toolbar, text="+ 添加任务", command=self._add_task).pack(side="left")
        ttk.Button(toolbar, text="全部开启", command=self._start_all_tasks).pack(side="left", padx=4)
        ttk.Button(toolbar, text="全部关闭", command=self._stop_all_tasks).pack(side="left", padx=4)

        list_frame = ttk.Frame(f)
        list_frame.pack(fill="both", expand=True, padx=8, pady=4)

        cols = ("name", "interval", "duration", "gif", "enabled")
        self._task_tree = ttk.Treeview(list_frame, columns=cols, show="headings")
        for col, hdr, w in zip(
            cols,
            ["名称", "间隔(分钟)", "显示(秒)", "素材", "状态"],
            [160, 80, 80, 120, 50],
        ):
            self._task_tree.heading(col, text=hdr)
            self._task_tree.column(col, width=w)
        scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=self._task_tree.yview)
        self._task_tree.configure(yscrollcommand=scrollbar.set)
        self._task_tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        btn_frame = ttk.Frame(f)
        btn_frame.pack(pady=(4, 8))
        ttk.Button(btn_frame, text="编辑", command=self._edit_task).pack(side="left", padx=4)
        ttk.Button(btn_frame, text="删除", command=self._delete_task).pack(side="left", padx=4)
        ttk.Button(btn_frame, text="效果展示", command=self._trigger_task).pack(side="left", padx=4)

    def _add_task(self):
        dialog = _TaskDialog(self._root, self._materials)
        if dialog.result:
            config_manager.save_task(dialog.result)
            scheduler.get_scheduler().start_task(dialog.result["id"])
            self._refresh_tasks()

    def _edit_task(self):
        sel = self._task_tree.selection()
        if not sel:
            messagebox.showinfo("提示", "请先选中一个任务")
            return
        task_id = self._task_tree.item(sel[0])["values"][-1]
        task = config_manager.get_task(task_id)
        if not task:
            return
        dialog = _TaskDialog(self._root, self._materials, task)
        if dialog.result:
            config_manager.save_task(dialog.result)
            scheduler.get_scheduler().restart_task(dialog.result["id"])
            self._refresh_tasks()

    def _delete_task(self):
        sel = self._task_tree.selection()
        if not sel:
            return
        task_id = self._task_tree.item(sel[0])["values"][-1]
        if messagebox.askyesno("确认", "确定删除该任务？"):
            scheduler.get_scheduler().stop_task(task_id)
            config_manager.delete_task(task_id)
            self._refresh_tasks()

    def _trigger_task(self):
        sel = self._task_tree.selection()
        if not sel:
            return
        task_id = self._task_tree.item(sel[0])["values"][-1]
        scheduler.get_scheduler().trigger_now(task_id)

    def _start_all_tasks(self):
        for t in config_manager.get_all_tasks():
            t["enabled"] = True
            config_manager.save_task(t)
            scheduler.get_scheduler().start_task(t["id"])
        self._refresh_tasks()

    def _stop_all_tasks(self):
        scheduler.get_scheduler().stop_all()
        for t in config_manager.get_all_tasks():
            t["enabled"] = False
            config_manager.save_task(t)
        self._refresh_tasks()

    def _refresh_tasks(self):
        self._task_tree.delete(*self._task_tree.get_children())
        self._tasks = config_manager.get_all_tasks()
        for t in self._tasks:
            gif_name = ""
            for m in self._materials:
                if m["id"] == t.get("gif_id"):
                    gif_name = m["name"]
                    break
            enabled_str = "已启用" if t.get("enabled") else "已关闭"
            self._task_tree.insert(
                "",
                "end",
                values=(t["name"], t["interval_minutes"], t["duration_seconds"], gif_name, enabled_str, t["id"]),
            )

    # ─── 玩偶设置 ───────────────────────────────────────────

    def _build_settings_tab(self):
        container = self._settings_scroll.interior
        pad = ttk.Frame(container)
        pad.pack(fill="both", expand=True, padx=16, pady=16)

        ttk.Label(pad, text="玩偶设置", font=("Microsoft YaHei UI", 12, "bold")).pack(anchor="w", pady=(0, 12))

        dist_frame = ttk.LabelFrame(pad, text="跑动距离", padding=8)
        dist_frame.pack(fill="x", pady=(0, 8))
        ttk.Label(dist_frame, text="在右下角区域移动的最大像素距离").pack(anchor="w")
        dist_var = tk.IntVar(value=config_manager.get_pet_settings().get("travel_distance", 500))
        ttk.Scale(dist_frame, from_=100, to=1200, orient="h", length=400, variable=dist_var).pack(pady=4)
        dist_val_lbl = ttk.Label(dist_frame, text=f"{dist_var.get()} px")
        dist_val_lbl.pack()
        dist_var.trace_add("write", lambda *_: (
            dist_val_lbl.configure(text=f"{dist_var.get()} px"),
            self._save_settings_key("travel_distance", dist_var.get()),
        ))

        speed_frame = ttk.LabelFrame(pad, text="移动速度", padding=8)
        speed_frame.pack(fill="x", pady=(0, 8))
        ttk.Label(speed_frame, text="数值越小移动越快").pack(anchor="w")
        speed_var = tk.IntVar(value=config_manager.get_pet_settings().get("speed", 10))
        ttk.Scale(speed_frame, from_=2, to=80, orient="h", length=400, variable=speed_var).pack(pady=4)
        speed_val_lbl = ttk.Label(speed_frame, text=f"{speed_var.get()} ms/帧")
        speed_val_lbl.pack()
        speed_var.trace_add("write", lambda *_: (
            speed_val_lbl.configure(text=f"{speed_var.get()} ms/帧"),
            self._save_settings_key("speed", speed_var.get()),
        ))

        bottom_frame = ttk.LabelFrame(pad, text="距底部距离", padding=8)
        bottom_frame.pack(fill="x", pady=(0, 8))
        ttk.Label(bottom_frame, text="玩偶距屏幕下边界的像素距离（避开任务栏）").pack(anchor="w")
        bottom_var = tk.IntVar(value=config_manager.get_pet_settings().get("bottom_margin", 45))
        ttk.Scale(bottom_frame, from_=0, to=150, orient="h", length=400, variable=bottom_var).pack(pady=4)
        bottom_val_lbl = ttk.Label(bottom_frame, text=f"{bottom_var.get()} px")
        bottom_val_lbl.pack()
        bottom_var.trace_add("write", lambda *_: (
            bottom_val_lbl.configure(text=f"{bottom_var.get()} px"),
            self._save_settings_key("bottom_margin", bottom_var.get()),
        ))

        top_frame = ttk.LabelFrame(pad, text="窗口行为", padding=8)
        top_frame.pack(fill="x", pady=(0, 12))
        top_var = tk.BooleanVar(value=config_manager.get_pet_settings().get("is_always_on_top", True))
        ttk.Checkbutton(top_frame, text="窗口置顶（始终在其它窗口上方）", variable=top_var).pack(anchor="w")
        top_var.trace_add("write", lambda *_: self._save_settings_key("is_always_on_top", top_var.get()))


    def _save_settings_key(self, key, value):
        settings = config_manager.get_pet_settings()
        settings[key] = value
        config_manager.save_pet_settings(settings)


# ─── 对话框 ─────────────────────────────────────────────────


class _NewMaterialDialog:
    def __init__(self, parent, path):
        self.result = None
        win = tk.Toplevel(parent)
        win.title("添加素材")
        win.geometry("320x180")
        win.resizable(False, False)
        win.transient(parent)
        win.grab_set()
        win.update_idletasks()
        cx = parent.winfo_x() + (parent.winfo_width() - win.winfo_width()) // 2
        cy = parent.winfo_y() + 40
        win.geometry(f"+{cx}+{cy}")
        self._win = win

        ttk.Label(win, text="名称：").place(x=20, y=20)
        name_var = tk.StringVar(value=Path(path).stem)
        ttk.Entry(win, textvariable=name_var, width=28).place(x=80, y=20)

        ttk.Label(win, text="分类：").place(x=20, y=60)
        cats = ["护眼", "运动", "喝水", "自定义", "默认"]
        cat_var = tk.StringVar(value="自定义")
        ttk.Combobox(win, textvariable=cat_var, values=cats, state="readonly", width=15).place(x=80, y=60)

        def ok():
            self.result = (name_var.get(), cat_var.get())
            win.destroy()

        ttk.Button(win, text="确定", command=ok).place(x=80, y=120, width=70)
        ttk.Button(win, text="取消", command=win.destroy).place(x=160, y=120, width=70)
        win.wait_window()


class _TaskDialog:
    def __init__(self, parent, materials, task=None):
        self.result = None
        self._task = task or {
            "id": str(uuid.uuid4())[:8],
            "name": "",
            "interval_minutes": 30,
            "gif_id": "",
            "duration_seconds": 8,
            "enabled": True,
            "scale_percent": 1,
        }
        win = tk.Toplevel(parent)
        win.title("编辑任务" if task else "新建任务")
        win.geometry("440x640")
        win.resizable(False, False)
        win.transient(parent)
        win.grab_set()
        win.update_idletasks()
        cx = parent.winfo_x() + (parent.winfo_width() - 440) // 2
        cy = parent.winfo_y() + 40
        win.geometry(f"+{cx}+{cy}")

        f = ttk.Frame(win, padding=12)
        f.pack(fill="both", expand=True)

        # 三层叠加预览画布参数
        PW, PH = 260, 240
        SIZES = [
            (3, "#4CAF50", "∗3", 220),
            (2, "#2196F3", "∗2", 150),
            (1, "#F44336", "∗1",  80),
        ]

        def _draw_boxes(canvas):
            canvas.delete("box")
            cx, cy = PW // 2, PH // 2
            for mult, color, label, px in SIZES:
                x0 = cx - px // 2
                y0 = cy - px // 2
                canvas.create_rectangle(x0, y0, x0 + px, y0 + px,
                    outline=color, width=2, tags="box")
                canvas.create_text(x0 + px - 3, y0 + px - 3, text=label,
                    font=("Arial", 10, "bold"), fill=color, anchor="se", tags="box")

        def _load_img_for_canvas(path, target):
            from PIL import Image as PILImage
            img = PILImage.open(path).convert("RGBA")
            img.thumbnail((target, target), PILImage.LANCZOS)
            # 拉伸到 target×target，白底
            img = img.resize((target, target), PILImage.LANCZOS)
            bg = PILImage.new("RGBA", (target, target), (255, 255, 255, 255))
            return PILImage.alpha_composite(bg, img).convert("RGB")

        # ── 表单字段 ──────────────────────────────────────────
        ttk.Label(f, text="任务名称：").grid(row=0, column=0, sticky="w", pady=5, padx=(12, 0))
        name_var = tk.StringVar(value=self._task["name"])
        ttk.Entry(f, textvariable=name_var, width=24).grid(row=0, column=1, sticky="w", pady=5)

        ttk.Label(f, text="提醒间隔(分钟)：").grid(row=1, column=0, sticky="w", pady=5, padx=(12, 0))
        interval_var = tk.IntVar(value=self._task["interval_minutes"])
        ttk.Spinbox(f, from_=1, to=999, textvariable=interval_var, width=8).grid(row=1, column=1, sticky="w", pady=5)

        ttk.Label(f, text="显示时长(秒)：").grid(row=2, column=0, sticky="w", pady=5, padx=(12, 0))
        dur_var = tk.IntVar(value=self._task["duration_seconds"])
        ttk.Spinbox(f, from_=1, to=300, textvariable=dur_var, width=8).grid(row=2, column=1, sticky="w", pady=5)

        ttk.Label(f, text="分类筛选：").grid(row=3, column=0, sticky="w", pady=5, padx=(12, 0))
        categories = ["全部"] + sorted(set(m["category"] for m in materials))
        cat_var = tk.StringVar(value="全部")
        cat_combo = ttk.Combobox(f, textvariable=cat_var, values=categories,
                                   state="readonly", width=10)
        cat_combo.grid(row=3, column=1, sticky="w", pady=5)

        ttk.Label(f, text="绑定素材：").grid(row=4, column=0, sticky="w", pady=5, padx=(12, 0))
        gif_names = [m["name"] for m in materials]
        gif_ids   = [m["id"]  for m in materials]
        gif_var   = tk.StringVar()
        gif_combo = ttk.Combobox(f, textvariable=gif_var, values=gif_names,
                                   state="readonly", width=22)
        gif_combo.grid(row=4, column=1, sticky="w", pady=5)
        for i, m in enumerate(materials):
            if m["id"] == self._task.get("gif_id"):
                gif_combo.current(i)
                break

        ttk.Label(f, text="缩放倍数：").grid(row=5, column=0, sticky="w", pady=5, padx=(12, 0))
        scale_var = tk.IntVar(value=int(self._task.get("scale_percent", 1) * 100))
        scale_row = ttk.Frame(f)
        scale_row.grid(row=5, column=1, sticky="w", pady=5)
        ttk.Scale(scale_row, from_=10, to=400, orient="h", length=180,
                   variable=scale_var).pack(side="left")
        scale_lbl = ttk.Label(scale_row, text="1.0x")
        scale_lbl.pack(side="left", padx=4)

        # ── 三层叠加预览区 ────────────────────────────────────
        ttk.Label(f, text="尺寸对比（∗3外框/∗2中框/∗1小框）：").grid(
            row=6, column=0, columnspan=2, sticky="w", pady=(6, 2), padx=(12, 0))

        pc = tk.Canvas(f, width=PW, height=PH,
                        bg="#f5f5f5", highlightthickness=1, highlightbackground="#cccccc")
        pc.grid(row=7, column=0, columnspan=2, pady=4)
        _draw_boxes(pc)

        pc_img_ref = [None]   # 防止 PhotoImage 被 GC

        # 缓存原始 GIF 尺寸（避免重复读取文件）
        _orig_size = [None]

        def update_previews(*_):
            val = scale_var.get()
            scale_lbl.configure(text=f"{val/100:.1f}x")
            sel = gif_combo.current()
            pc.delete("gif")
            pc.delete("highlight")
            if sel < 0 or not gif_ids:
                return
            path = config_manager.get_material_path(gif_ids[sel])
            if not path:
                return
            # 获取原始尺寸（只读一次）
            if _orig_size[0] is None:
                from PIL import Image as PILImage
                _orig_size[0] = PILImage.open(path).convert("RGBA").size
            w0, h0 = _orig_size[0]
            scale = val / 100.0
            # 按缩放倍数计算实际像素尺寸，限制在 10~240px 之间
            tw = max(10, min(int(w0 * scale), 240))
            th = max(10, min(int(h0 * scale), 240))
            # 加载并缩放 GIF（填满 tw×th 区域）
            img = _load_img_for_canvas(path, max(tw, th))
            # 裁剪/缩放为目标尺寸 tw × th
            from PIL import Image as PILImage
            img = img.resize((tw, th), PILImage.LANCZOS)
            from PIL import ImageTk as PILImageTk
            ph = PILImageTk.PhotoImage(img)
            pc_img_ref[0] = ph
            pc.create_image(PW // 2, PH // 2, image=ph, tags="gif")
            # 高亮最接近当前缩放的框
            closest = min(SIZES, key=lambda s: abs(val / 100.0 - s[0]))
            _, color, label, px = closest
            x0 = PW // 2 - px // 2
            y0 = PH // 2 - px // 2
            pc.create_rectangle(x0 - 3, y0 - 3, x0 + px + 3, y0 + px + 3,
                                outline="#ff9800", width=3, tags="highlight")

        # ── 分类切换 ─────────────────────────────────────────
        def on_cat_change(*_):
            _orig_size[0] = None
            sel_cat = cat_var.get()
            if sel_cat == "全部":
                opts = [m["name"] for m in materials]
                ids  = [m["id"]  for m in materials]
            else:
                opts = [m["name"] for m in materials if m["category"] == sel_cat]
                ids  = [m["id"]  for m in materials if m["category"] == sel_cat]
            gif_combo.configure(values=opts)
            gif_names[:] = opts
            gif_ids[:]   = ids
            if opts:
                gif_combo.current(0)
                update_previews()
            else:
                gif_combo.set("")
                pc.delete("gif")
        cat_var.trace_add("write", on_cat_change)

        # ── 拖拽 GIF ─────────────────────────────────────────
        def _load_dropped(path_str):
            path = (path_str or "").strip().strip('"').strip("{").strip("}").split()[0]
            if path and path.lower().endswith(".gif"):
                try:
                    from PIL import ImageTk as PILImageTk
                    target = SIZES[2][3] - 8
                    img = _load_img_for_canvas(path, target)
                    ph = PILImageTk.PhotoImage(img)
                    pc_img_ref[0] = ph
                    pc.delete("gif")
                    pc.create_image(PW // 2, PH // 2, image=ph, tags="gif")
                except Exception:
                    pass

        try:
            from tkinterdnd2 import DND_FILES
            pc.drop_target_register(DND_FILES)
            pc.dnd_bind("<<Drop>>", lambda e: _load_dropped(e.data))
        except Exception:
            pass

        # ── 启用 + 按钮 ──────────────────────────────────────
        enabled_var = tk.BooleanVar(value=self._task.get("enabled", True))
        ttk.Checkbutton(f, text="创建后立即启用", variable=enabled_var).grid(
            row=8, column=0, columnspan=2, sticky="w", pady=5, padx=(12, 0))

        def ok():
            sel = gif_combo.current()
            gid = gif_ids[sel] if sel >= 0 else ""
            if not name_var.get().strip():
                messagebox.showwarning("提示", "请输入任务名称")
                return
            if not gid:
                messagebox.showwarning("提示", "请选择素材")
                return
            self._task["name"]            = name_var.get().strip()
            self._task["interval_minutes"] = interval_var.get()
            self._task["duration_seconds"]  = dur_var.get()
            self._task["gif_id"]           = gid
            self._task["enabled"]          = enabled_var.get()
            self._task["scale_percent"]    = scale_var.get() / 100.0
            self.result = self._task
            win.destroy()

        btn_f = ttk.Frame(f)
        btn_f.grid(row=9, column=0, columnspan=2, pady=10)
        ttk.Button(btn_f, text="确定", command=ok).pack(side="left", padx=8)
        ttk.Button(btn_f, text="取消", command=win.destroy).pack(side="left")

        gif_combo.bind("<<ComboboxSelected>>", lambda _: (_orig_size.__setitem__(0, None), update_previews()))
        scale_var.trace_add("write", update_previews)
        update_previews()

        win.wait_window()
