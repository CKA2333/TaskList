"""
Desktop Floating Task List — Phase Management + bilingual UI (EN / CH)
- Drag ⠿ to move tasks between phases
- Add / remove phases freely
- Toggle language with Ctrl+L or the EN/中 button in the header
- All data auto-saved to tasks.json
"""

import tkinter as tk
from tkinter import font as tkfont
import json
import os

DATA_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tasks.json")

# ─── Color theme ──────────────────────────────────────────────────────────────
BG          = "#1e1e2e"
HEADER_BG   = "#181825"
ITEM_BG     = "#2a2a3e"
ITEM_HOVER  = "#313145"
CHECK_ON    = "#a6e3a1"
CHECK_OFF   = "#585b70"
TEXT_MAIN   = "#cdd6f4"
TEXT_DONE   = "#6c7086"
ACCENT      = "#89b4fa"
ADD_BG      = "#313145"
ENTRY_BG    = "#313145"
ENTRY_FG    = "#cdd6f4"
RED         = "#f38ba8"
SCROLLBAR   = "#45475a"
PHASE_HDR   = "#181825"   # same as header bar for a clean section look
PHASE_HILITE= "#2a2a4e"   # phase header highlight color during drag

WINDOW_W    = 320
WINDOW_H    = 500

# ─── i18n string table ────────────────────────────────────────────────────────
STRINGS = {
    "ch": {
        "title":         "📋  Task List",
        "lang_btn":      "EN",          # label shows the language you'll switch TO
        "lang_tip":      "切换语言 (Ctrl+L)",
        "pin_tip":       "置顶 / 取消置顶",
        "phase_sel_tip": "新任务加入哪个 Phase（点击切换）",
        "progress":      lambda d, t, p: f"{d}/{t} 完成  ({p}%)" if t else "暂无任务，添加一个吧 ✨",
        "phase_empty":   "— 拖拽任务到此处 —",
        "add_phase":     "＋ 添加 Phase",
        "phase_label":   lambda n: f"  Phase {n}",
        "default_tasks": [
            ("欢迎使用 Task List ✨",           1),
            ("双击任务文字可以编辑",             1),
            ("拖动 ⠿ 把任务移到不同 Phase",     1),
            ("Phase 1 = 最高优先级",            1),
            ("底部 P1 切换新任务的默认 Phase",   2),
            ("点击 Phase 右侧 ✕ 可删除 Phase",  2),
        ],
    },
    "en": {
        "title":         "📋  Task List",
        "lang_btn":      "中",
        "lang_tip":      "Switch language (Ctrl+L)",
        "pin_tip":       "Pin / Unpin",
        "phase_sel_tip": "Phase for new tasks (click to cycle)",
        "progress":      lambda d, t, p: f"{d}/{t} done  ({p}%)" if t else "No tasks yet ✨",
        "phase_empty":   "— Drop tasks here —",
        "add_phase":     "＋ Add Phase",
        "phase_label":   lambda n: f"  Phase {n}",
        "default_tasks": [
            ("Welcome to Task List ✨",              1),
            ("Double-click a task to edit it",       1),
            ("Drag ⠿ to move tasks between phases",  1),
            ("Phase 1 = highest priority",           1),
            ("Tap P1 below to pick default phase",   2),
            ("Click ✕ on a phase header to delete",  2),
        ],
    },
}


class TaskItem:
    def __init__(self, text: str, done: bool = False, phase: int = 1):
        self.text  = text
        self.done  = done
        self.phase = phase


class TaskListApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.overrideredirect(True)
        self.attributes("-topmost", True)
        self.attributes("-alpha", 0.97)
        self.configure(bg=BG)
        self.resizable(False, False)

        self._pinned    = True
        self._drag_x    = 0
        self._drag_y    = 0
        self._edit_item = None

        # Task drag state
        self._dragging_task_idx    = None
        self._task_drag_active     = False
        self._drag_ghost           = None
        self._drag_highlight_phase = None
        self._phase_section_frames = {}   # phase_num -> outer Frame
        self._phase_header_frames  = {}   # phase_num -> header Frame

        # Phase selected for new tasks in the input bar
        self._input_phase = 1

        # Language ("ch" or "en")
        self._lang = "ch"

        # Fonts
        self.font_title = tkfont.Font(family="Segoe UI", size=11, weight="bold")
        self.font_task  = tkfont.Font(family="Segoe UI", size=10)
        self.font_done  = tkfont.Font(family="Segoe UI", size=10, overstrike=True)
        self.font_small = tkfont.Font(family="Segoe UI", size=9)
        self.font_add   = tkfont.Font(family="Segoe UI", size=13, weight="bold")

        self.phases: list[int]     = [1]
        self.tasks:  list[TaskItem] = []
        self._load()

        self._build_ui()
        self._refresh_list()
        self._center_window()

    # ── i18n helper ───────────────────────────────────────────────────────────
    def _t(self, key):
        """Return the UI string for the current language."""
        return STRINGS[self._lang][key]

    def _toggle_lang(self, event=None):
        self._lang = "en" if self._lang == "ch" else "ch"
        self._apply_lang()
        self._save()

    def _apply_lang(self):
        """Push current language to all static labels, then redraw dynamic list."""
        self._title_lbl.config(text=self._t("title"))
        self._lang_btn.config(text=self._t("lang_btn"))
        self._refresh_list()

    # ── Build UI ──────────────────────────────────────────────────────────────
    def _build_ui(self):
        self.geometry(f"{WINDOW_W}x{WINDOW_H}")

        # Header bar
        header = tk.Frame(self, bg=HEADER_BG, height=44)
        header.pack(fill="x", side="top")
        header.pack_propagate(False)
        header.bind("<ButtonPress-1>", self._drag_start)
        header.bind("<B1-Motion>",     self._drag_move)

        self._title_lbl = tk.Label(header, text=self._t("title"),
                                   bg=HEADER_BG, fg=TEXT_MAIN,
                                   font=self.font_title, anchor="w", padx=14)
        self._title_lbl.pack(side="left", fill="y")
        self._title_lbl.bind("<ButtonPress-1>", self._drag_start)
        self._title_lbl.bind("<B1-Motion>",     self._drag_move)

        btn_area = tk.Frame(header, bg=HEADER_BG)
        btn_area.pack(side="right", padx=8)

        # Language toggle button
        self._lang_btn = tk.Label(btn_area, text=self._t("lang_btn"),
                                  bg=HEADER_BG, fg=TEXT_DONE,
                                  font=self.font_small, cursor="hand2", padx=4)
        self._lang_btn.pack(side="left")
        self._lang_btn.bind("<Button-1>", self._toggle_lang)
        self._lang_btn.bind("<Enter>", lambda e: self._lang_btn.config(fg=ACCENT))
        self._lang_btn.bind("<Leave>", lambda e: self._lang_btn.config(fg=TEXT_DONE))
        _tooltip(self._lang_btn, lambda: self._t("lang_tip"))

        # Pin button
        self._pin_btn = tk.Label(btn_area, text="📌", bg=HEADER_BG,
                                 fg=ACCENT, font=self.font_small,
                                 cursor="hand2", padx=4)
        self._pin_btn.pack(side="left")
        self._pin_btn.bind("<Button-1>", self._toggle_pin)
        _tooltip(self._pin_btn, lambda: self._t("pin_tip"))

        # Close button
        close_btn = tk.Label(btn_area, text="✕", bg=HEADER_BG,
                             fg=TEXT_DONE, font=self.font_title,
                             cursor="hand2", padx=6)
        close_btn.pack(side="left")
        close_btn.bind("<Button-1>", lambda e: self.destroy())
        close_btn.bind("<Enter>", lambda e: close_btn.config(fg=RED))
        close_btn.bind("<Leave>", lambda e: close_btn.config(fg=TEXT_DONE))

        # Progress label
        self._progress_frame = tk.Frame(self, bg=BG, height=24)
        self._progress_frame.pack(fill="x", padx=14, pady=(6, 0))
        self._progress_lbl = tk.Label(self._progress_frame, text="",
                                      bg=BG, fg=TEXT_DONE,
                                      font=self.font_small, anchor="w")
        self._progress_lbl.pack(side="left")

        # Scrollable task list
        list_container = tk.Frame(self, bg=BG)
        list_container.pack(fill="both", expand=True, padx=8, pady=4)

        self._canvas = tk.Canvas(list_container, bg=BG,
                                 highlightthickness=0, bd=0)
        scrollbar = tk.Scrollbar(list_container, orient="vertical",
                                 command=self._canvas.yview,
                                 bg=BG, troughcolor=BG,
                                 activebackground=SCROLLBAR)
        self._canvas.configure(yscrollcommand=scrollbar.set)
        self._canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        self._list_frame = tk.Frame(self._canvas, bg=BG)
        self._canvas_window = self._canvas.create_window(
            (0, 0), window=self._list_frame, anchor="nw")
        self._list_frame.bind("<Configure>", self._on_frame_configure)
        self._canvas.bind("<Configure>",     self._on_canvas_configure)
        self._canvas.bind("<MouseWheel>",    self._on_mousewheel)

        # Bottom input bar
        bottom = tk.Frame(self, bg=HEADER_BG, height=50)
        bottom.pack(fill="x", side="bottom")
        bottom.pack_propagate(False)

        self._entry_var = tk.StringVar()
        entry = tk.Entry(bottom, textvariable=self._entry_var,
                         bg=ENTRY_BG, fg=ENTRY_FG, insertbackground=TEXT_MAIN,
                         relief="flat", font=self.font_task,
                         highlightthickness=1, highlightcolor=ACCENT,
                         highlightbackground=ADD_BG)
        entry.pack(side="left", fill="both", expand=True, padx=(12, 4), pady=10)
        entry.bind("<Return>", self._add_task_from_entry)

        # Phase selector badge (cycles through phases on click)
        self._phase_sel_lbl = tk.Label(bottom, text=f"P{self._input_phase}",
                                       bg=ADD_BG, fg=ACCENT,
                                       font=self.font_small, width=3,
                                       cursor="hand2")
        self._phase_sel_lbl.pack(side="left", pady=10, fill="y")
        self._phase_sel_lbl.bind("<Button-1>", self._cycle_input_phase)
        _tooltip(self._phase_sel_lbl, lambda: self._t("phase_sel_tip"))

        # Add task button
        add_btn = tk.Label(bottom, text="+", bg=ACCENT,
                           fg=HEADER_BG, font=self.font_add,
                           width=3, cursor="hand2")
        add_btn.pack(side="right", padx=(4, 12), pady=10, fill="y")
        add_btn.bind("<Button-1>", self._add_task_from_entry)
        add_btn.bind("<Enter>", lambda e: add_btn.config(bg=TEXT_MAIN))
        add_btn.bind("<Leave>", lambda e: add_btn.config(bg=ACCENT))

        # Global keyboard shortcut: Ctrl+L toggles language
        self.bind_all("<Control-l>", self._toggle_lang)

    # ── Render ────────────────────────────────────────────────────────────────
    def _refresh_list(self):
        for w in self._list_frame.winfo_children():
            w.destroy()
        self._phase_section_frames = {}
        self._phase_header_frames  = {}

        done_count = sum(1 for t in self.tasks if t.done)
        total = len(self.tasks)
        pct = int(done_count / total * 100) if total else 0
        progress_fn = self._t("progress")
        self._progress_lbl.config(text=progress_fn(done_count, total, pct))

        for phase_num in sorted(self.phases):
            self._make_phase_section(phase_num)

        self._make_add_phase_button()
        self._list_frame.update_idletasks()

        # Keep input phase valid after phases may have changed
        if self._input_phase not in self.phases:
            self._input_phase = min(self.phases)
        self._phase_sel_lbl.config(text=f"P{self._input_phase}")

    def _make_phase_section(self, phase_num: int):
        # Outer wrapper — used for drop-target hit detection
        section = tk.Frame(self._list_frame, bg=BG)
        section.pack(fill="x", padx=2, pady=(0, 2))
        self._phase_section_frames[phase_num] = section
        section.bind("<MouseWheel>", self._on_mousewheel)

        # Phase section header
        hdr = tk.Frame(section, bg=PHASE_HDR)
        hdr.pack(fill="x")
        self._phase_header_frames[phase_num] = hdr
        hdr.bind("<MouseWheel>", self._on_mousewheel)

        phase_lbl_fn = self._t("phase_label")
        hdr_lbl = tk.Label(hdr, text=phase_lbl_fn(phase_num),
                           bg=PHASE_HDR, fg=ACCENT,
                           font=self.font_small, anchor="w", pady=5)
        hdr_lbl.pack(side="left")
        hdr_lbl.bind("<MouseWheel>", self._on_mousewheel)

        # Delete phase button (requires at least one phase to remain)
        if len(self.phases) > 1:
            del_btn = tk.Label(hdr, text="✕", fg=TEXT_DONE,
                               bg=PHASE_HDR, font=self.font_small,
                               cursor="hand2", padx=8)
            del_btn.pack(side="right")
            del_btn.bind("<Button-1>", lambda e, p=phase_num: self._delete_phase(p))
            del_btn.bind("<Enter>", lambda e: del_btn.config(fg=RED))
            del_btn.bind("<Leave>", lambda e: del_btn.config(fg=TEXT_DONE))

        # Tasks belonging to this phase
        phase_tasks = [(i, t) for i, t in enumerate(self.tasks) if t.phase == phase_num]
        for idx, task in phase_tasks:
            self._make_task_row(idx, task, section)

        # Empty-phase placeholder
        if not phase_tasks:
            ph_lbl = tk.Label(section, text=self._t("phase_empty"),
                              bg=BG, fg=TEXT_DONE,
                              font=self.font_small, pady=6)
            ph_lbl.pack()
            ph_lbl.bind("<MouseWheel>", self._on_mousewheel)

        # Separator line between sections
        sep = tk.Frame(self._list_frame, bg=SCROLLBAR, height=1)
        sep.pack(fill="x", padx=8, pady=(0, 2))

    def _make_add_phase_button(self):
        btn_frame = tk.Frame(self._list_frame, bg=BG)
        btn_frame.pack(fill="x", pady=6)
        btn_frame.bind("<MouseWheel>", self._on_mousewheel)

        btn = tk.Label(btn_frame, text=self._t("add_phase"),
                       bg=BG, fg=TEXT_DONE,
                       font=self.font_small, cursor="hand2")
        btn.pack()
        btn.bind("<Button-1>", self._add_phase)
        btn.bind("<Enter>",    lambda e: btn.config(fg=ACCENT))
        btn.bind("<Leave>",    lambda e: btn.config(fg=TEXT_DONE))
        btn.bind("<MouseWheel>", self._on_mousewheel)

    def _make_task_row(self, idx: int, task: TaskItem, parent: tk.Frame):
        row = tk.Frame(parent, bg=ITEM_BG, pady=5, padx=6, cursor="arrow")
        row.pack(fill="x", padx=4, pady=2)

        hover_widgets: list[tk.Widget] = []

        def on_enter(e):
            row.config(bg=ITEM_HOVER)
            for w in hover_widgets:
                try: w.config(bg=ITEM_HOVER)
                except tk.TclError: pass

        def on_leave(e):
            row.config(bg=ITEM_BG)
            for w in hover_widgets:
                try: w.config(bg=ITEM_BG)
                except tk.TclError: pass

        row.bind("<Enter>",      on_enter)
        row.bind("<Leave>",      on_leave)
        row.bind("<MouseWheel>", self._on_mousewheel)

        # Drag handle
        drag_handle = tk.Label(row, text="⠿", fg=TEXT_DONE, bg=ITEM_BG,
                               font=self.font_small, cursor="fleur", padx=2)
        drag_handle.pack(side="left")
        hover_widgets.append(drag_handle)
        drag_handle.bind("<ButtonPress-1>",
                         lambda e, i=idx, h=drag_handle: self._drag_task_start(e, i, h))
        drag_handle.bind("<Enter>",
                         lambda e: (on_enter(e), drag_handle.config(fg=TEXT_MAIN)))
        drag_handle.bind("<Leave>",
                         lambda e: (on_leave(e), drag_handle.config(fg=TEXT_DONE)))

        # Checkbox
        chk_lbl = tk.Label(row,
                           text="✔" if task.done else "○",
                           fg=CHECK_ON if task.done else CHECK_OFF,
                           bg=ITEM_BG, font=self.font_task,
                           cursor="hand2", width=2)
        chk_lbl.pack(side="left")
        hover_widgets.append(chk_lbl)
        chk_lbl.bind("<Button-1>", lambda e, i=idx: self._toggle_task(i))
        chk_lbl.bind("<Enter>",    on_enter)
        chk_lbl.bind("<Leave>",    on_leave)

        # Task text label
        text_lbl = tk.Label(row,
                            text=task.text,
                            fg=TEXT_DONE if task.done else TEXT_MAIN,
                            bg=ITEM_BG,
                            font=self.font_done if task.done else self.font_task,
                            anchor="w", justify="left",
                            wraplength=WINDOW_W - 110,
                            cursor="xterm")
        text_lbl.pack(side="left", fill="x", expand=True, padx=(4, 0))
        hover_widgets.append(text_lbl)
        text_lbl.bind("<Double-Button-1>",
                      lambda e, i=idx, lbl=text_lbl, r=row: self._start_edit(i, lbl, r))
        text_lbl.bind("<Enter>",      on_enter)
        text_lbl.bind("<Leave>",      on_leave)
        text_lbl.bind("<MouseWheel>", self._on_mousewheel)

        # Delete button
        del_btn = tk.Label(row, text="✕", fg=RED, bg=ITEM_BG,
                           font=self.font_small, cursor="hand2", padx=4)
        del_btn.pack(side="right")
        hover_widgets.append(del_btn)
        del_btn.bind("<Button-1>", lambda e, i=idx: self._delete_task(i))
        del_btn.bind("<Enter>",    on_enter)
        del_btn.bind("<Leave>",    on_leave)

    # ── Task drag & drop ──────────────────────────────────────────────────────
    def _drag_task_start(self, event, task_idx: int, handle: tk.Widget):
        if self._edit_item is not None:
            return
        self._dragging_task_idx = task_idx
        self._task_drag_active  = True

        # Ghost label that follows the cursor
        raw     = self.tasks[task_idx].text
        display = (raw[:24] + "…") if len(raw) > 24 else raw
        self._drag_ghost = tk.Toplevel(self)
        self._drag_ghost.overrideredirect(True)
        self._drag_ghost.attributes("-alpha", 0.80)
        self._drag_ghost.attributes("-topmost", True)
        tk.Label(self._drag_ghost, text=f"  {display}  ",
                 bg=ACCENT, fg=HEADER_BG,
                 font=self.font_small, pady=4).pack()
        self._drag_ghost.geometry(f"+{event.x_root + 12}+{event.y_root + 12}")

        # Grab all mouse events to the handle widget while dragging
        handle.grab_set()
        handle.bind("<B1-Motion>",
                    lambda e, h=handle: self._drag_task_motion(e, h))
        handle.bind("<ButtonRelease-1>",
                    lambda e, h=handle: self._drag_task_release(e, h))

    def _drag_task_motion(self, event, handle: tk.Widget):
        if not self._task_drag_active:
            return
        if self._drag_ghost:
            self._drag_ghost.geometry(f"+{event.x_root + 12}+{event.y_root + 12}")

        # Highlight the phase section under the cursor
        target = self._get_phase_at_screen_y(event.y_root)
        if target != self._drag_highlight_phase:
            self._set_phase_highlight(self._drag_highlight_phase, False)
            self._drag_highlight_phase = target
            self._set_phase_highlight(target, True)

    def _drag_task_release(self, event, handle: tk.Widget):
        if not self._task_drag_active:
            return
        handle.grab_release()
        handle.unbind("<B1-Motion>")
        handle.unbind("<ButtonRelease-1>")

        target = self._get_phase_at_screen_y(event.y_root)
        if target is not None and self._dragging_task_idx is not None:
            self.tasks[self._dragging_task_idx].phase = target
            self._save()

        # Clean up drag state
        self._set_phase_highlight(self._drag_highlight_phase, False)
        if self._drag_ghost:
            self._drag_ghost.destroy()
            self._drag_ghost = None
        self._task_drag_active     = False
        self._dragging_task_idx    = None
        self._drag_highlight_phase = None
        self._refresh_list()

    def _get_phase_at_screen_y(self, y_root: int):
        """Return the phase number whose section frame contains screen-y, or None."""
        for phase_num, frame in self._phase_section_frames.items():
            try:
                y_top = frame.winfo_rooty()
                y_bot = y_top + frame.winfo_height()
                if y_top <= y_root <= y_bot:
                    return phase_num
            except tk.TclError:
                pass
        return None

    def _set_phase_highlight(self, phase_num, highlight: bool):
        """Highlight or un-highlight a phase section header."""
        if phase_num is None:
            return
        hdr = self._phase_header_frames.get(phase_num)
        if not hdr:
            return
        color = PHASE_HILITE if highlight else PHASE_HDR
        try:
            hdr.config(bg=color)
            for child in hdr.winfo_children():
                try: child.config(bg=color)
                except tk.TclError: pass
        except tk.TclError:
            pass

    # ── Phase management ──────────────────────────────────────────────────────
    def _add_phase(self, event=None):
        new_num = max(self.phases) + 1
        self.phases.append(new_num)
        self._save()
        self._refresh_list()
        self._canvas.after(50, lambda: self._canvas.yview_moveto(1.0))

    def _delete_phase(self, phase_num: int):
        """Remove a phase, moving its tasks to the first remaining phase."""
        if len(self.phases) <= 1:
            return
        remaining = sorted(p for p in self.phases if p != phase_num)
        fallback  = remaining[0]
        for task in self.tasks:
            if task.phase == phase_num:
                task.phase = fallback
        self.phases.remove(phase_num)
        self._renumber_phases()
        self._save()
        self._refresh_list()

    def _renumber_phases(self):
        """Compact phases back to 1, 2, 3, … after a deletion."""
        old_sorted = sorted(self.phases)
        mapping    = {old: i + 1 for i, old in enumerate(old_sorted)}
        self.phases = list(range(1, len(old_sorted) + 1))
        for task in self.tasks:
            task.phase = mapping.get(task.phase, 1)

    # ── Input phase selector ──────────────────────────────────────────────────
    def _cycle_input_phase(self, event=None):
        """Cycle the default phase for newly added tasks."""
        sorted_phases = sorted(self.phases)
        cur_idx = sorted_phases.index(self._input_phase) \
                  if self._input_phase in sorted_phases else 0
        self._input_phase = sorted_phases[(cur_idx + 1) % len(sorted_phases)]
        self._phase_sel_lbl.config(text=f"P{self._input_phase}")

    # ── Inline edit ───────────────────────────────────────────────────────────
    def _start_edit(self, idx: int, label: tk.Label, row: tk.Frame):
        if self._edit_item is not None:
            return
        self._edit_item = idx
        var = tk.StringVar(value=self.tasks[idx].text)
        entry = tk.Entry(row, textvariable=var,
                         bg=ENTRY_BG, fg=ENTRY_FG,
                         insertbackground=TEXT_MAIN,
                         relief="flat", font=self.font_task,
                         highlightthickness=1, highlightcolor=ACCENT,
                         highlightbackground=ACCENT)
        label.pack_forget()
        entry.pack(side="left", fill="x", expand=True, padx=(4, 0))
        entry.focus_set()
        entry.select_range(0, "end")

        def commit(e=None):
            new_text = var.get().strip()
            if new_text:
                self.tasks[idx].text = new_text
                self._save()
            self._edit_item = None
            self._refresh_list()

        def cancel(e=None):
            self._edit_item = None
            self._refresh_list()

        entry.bind("<Return>",   commit)
        entry.bind("<Escape>",   cancel)
        entry.bind("<FocusOut>", commit)

    # ── Task operations ───────────────────────────────────────────────────────
    def _toggle_task(self, idx: int):
        self.tasks[idx].done = not self.tasks[idx].done
        self._save()
        self._refresh_list()

    def _delete_task(self, idx: int):
        self.tasks.pop(idx)
        self._save()
        self._refresh_list()

    def _add_task_from_entry(self, event=None):
        text = self._entry_var.get().strip()
        if not text:
            return
        if self._input_phase not in self.phases:
            self._input_phase = min(self.phases)
        self.tasks.append(TaskItem(text, phase=self._input_phase))
        self._entry_var.set("")
        self._save()
        self._refresh_list()
        self._canvas.after(50, lambda: self._canvas.yview_moveto(1.0))

    # ── Scroll ────────────────────────────────────────────────────────────────
    def _on_frame_configure(self, event):
        self._canvas.configure(scrollregion=self._canvas.bbox("all"))

    def _on_canvas_configure(self, event):
        self._canvas.itemconfig(self._canvas_window, width=event.width)

    def _on_mousewheel(self, event):
        self._canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    # ── Pin / window drag ─────────────────────────────────────────────────────
    def _toggle_pin(self, event=None):
        self._pinned = not self._pinned
        self.attributes("-topmost", self._pinned)
        self._pin_btn.config(fg=ACCENT if self._pinned else TEXT_DONE)

    def _drag_start(self, event):
        self._drag_x = event.x_root - self.winfo_x()
        self._drag_y = event.y_root - self.winfo_y()

    def _drag_move(self, event):
        if self._task_drag_active:
            return  # don't move window while a task is being dragged
        x = event.x_root - self._drag_x
        y = event.y_root - self._drag_y
        self.geometry(f"+{x}+{y}")

    # ── Persistence ───────────────────────────────────────────────────────────
    def _save(self):
        data = {
            "lang":   self._lang,
            "phases": self.phases,
            "tasks":  [{"text": t.text, "done": t.done, "phase": t.phase}
                       for t in self.tasks],
        }
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def _load(self):
        if not os.path.exists(DATA_FILE):
            # First launch — create bilingual demo tasks
            self.phases = [1, 2]
            self.tasks  = [TaskItem(text, phase=p)
                           for text, p in self._t("default_tasks")]
            return
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                raw = json.load(f)

            # Migrate old format (plain list) to new dict format
            if isinstance(raw, list):
                self.phases = [1]
                self.tasks  = [TaskItem(d["text"], d.get("done", False), phase=1)
                               for d in raw]
            else:
                self._lang  = raw.get("lang", "ch")
                self.phases = raw.get("phases", [1])
                self.tasks  = [
                    TaskItem(d["text"], d.get("done", False), d.get("phase", 1))
                    for d in raw.get("tasks", [])
                ]
        except Exception:
            self.phases = [1]
            self.tasks  = []

    # ── Window position ───────────────────────────────────────────────────────
    def _center_window(self):
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        x  = sw - WINDOW_W - 40
        y  = (sh - WINDOW_H) // 2
        self.geometry(f"{WINDOW_W}x{WINDOW_H}+{x}+{y}")


def _tooltip(widget, text_fn):
    """Attach a floating tooltip to widget. text_fn is a callable () -> str."""
    tip = None

    def show(e):
        nonlocal tip
        tip = tk.Toplevel(widget)
        tip.overrideredirect(True)
        tip.attributes("-topmost", True)
        lbl = tk.Label(tip, text=text_fn(), bg="#313145", fg=TEXT_MAIN,
                       font=("Segoe UI", 8), padx=6, pady=3, relief="flat")
        lbl.pack()
        x = widget.winfo_rootx() + 20
        y = widget.winfo_rooty() + 20
        tip.geometry(f"+{x}+{y}")

    def hide(e):
        nonlocal tip
        if tip:
            tip.destroy()
            tip = None

    widget.bind("<Enter>", show)
    widget.bind("<Leave>", hide)


if __name__ == "__main__":
    app = TaskListApp()
    app.mainloop()
