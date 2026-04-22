"""
Advanced To-Do List Application
================================
A feature-rich GUI-based task manager built with Python and Tkinter.

Features:
  - Add, Edit, Delete, Complete tasks
  - Task Priority (High / Medium / Low)
  - Due date picker (DateEntry via tkcalendar)
  - Search / filter tasks
  - Dark / Light theme toggle
  - Persistent JSON storage
  - PEP 8 compliant, OOP design

Requirements:
  pip install tkcalendar
"""

import json
import os
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
from datetime import datetime, date

# Try importing tkcalendar; fall back gracefully if not installed
try:
    from tkcalendar import DateEntry
    HAS_CALENDAR = True
except ImportError:
    HAS_CALENDAR = False

# ──────────────────────────────────────────────────────────────
# Constants
# ──────────────────────────────────────────────────────────────
DATA_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tasks.json")

PRIORITY_COLORS = {
    "High":   "#ef4444",
    "Medium": "#f59e0b",
    "Low":    "#22c55e",
}

THEMES = {
    "dark": {
        "bg":            "#0c100e",
        "surface":       "#1b241e",
        "surface2":      "#27362c",
        "accent":        "#378c56",
        "accent_hover":  "#42a667",
        "text":          "#ebe8df",
        "subtext":       "#8b9b92",
        "border":        "#27362c",
        "done_fg":       "#45584d",
        "entry_bg":      "#1b241e",
        "entry_fg":      "#ebe8df",
        "btn_fg":        "#ffffff",
        "delete_bg":     "#ab4a4a",
        "delete_hover":  "#c05c5c",
        "complete_bg":   "#378c56",
        "complete_hover":"#42a667",
        "edit_bg":       "#4a7a9c",
        "edit_hover":    "#5c91b5",
    },
    "light": {
        "bg":            "#f8fafc",
        "surface":       "#ffffff",
        "surface2":      "#e2e8f0",
        "accent":        "#6366f1",
        "accent_hover":  "#4f46e5",
        "text":          "#0f172a",
        "subtext":       "#64748b",
        "border":        "#e2e8f0",
        "done_fg":       "#94a3b8",
        "entry_bg":      "#ffffff",
        "entry_fg":      "#0f172a",
        "btn_fg":        "#ffffff",
        "delete_bg":     "#dc2626",
        "delete_hover":  "#b91c1c",
        "complete_bg":   "#16a34a",
        "complete_hover":"#15803d",
        "edit_bg":       "#2563eb",
        "edit_hover":    "#1d4ed8",
    },
}


# ──────────────────────────────────────────────────────────────
# Data Model
# ──────────────────────────────────────────────────────────────
class Task:
    """Represents a single to-do task."""

    def __init__(self, task_id: int, title: str, priority: str = "Medium",
                 due_date: str = "", completed: bool = False,
                 created_at: str = ""):
        self.task_id    = task_id
        self.title      = title
        self.priority   = priority          # "High" | "Medium" | "Low"
        self.due_date   = due_date          # ISO string "YYYY-MM-DD" or ""
        self.completed  = completed
        self.created_at = created_at or datetime.now().strftime("%Y-%m-%d %H:%M")

    # ── Serialisation ──────────────────────────────────────────
    def to_dict(self) -> dict:
        return {
            "task_id":    self.task_id,
            "title":      self.title,
            "priority":   self.priority,
            "due_date":   self.due_date,
            "completed":  self.completed,
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Task":
        return cls(
            task_id    = data.get("task_id", 0),
            title      = data.get("title", ""),
            priority   = data.get("priority", "Medium"),
            due_date   = data.get("due_date", ""),
            completed  = data.get("completed", False),
            created_at = data.get("created_at", ""),
        )

    def __str__(self) -> str:
        status = "✔" if self.completed else "○"
        due    = f"  📅 {self.due_date}" if self.due_date else ""
        return f"{status}  {self.title}{due}"


# ──────────────────────────────────────────────────────────────
# Storage Manager
# ──────────────────────────────────────────────────────────────
class TaskStorage:
    """Handles JSON-based persistence for tasks."""

    @staticmethod
    def load() -> list[Task]:
        """Load tasks from the JSON file."""
        try:
            if not os.path.exists(DATA_FILE):
                return []
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                raw = json.load(f)
            return [Task.from_dict(item) for item in raw]
        except (json.JSONDecodeError, KeyError, TypeError) as exc:
            messagebox.showerror("Load Error", f"Could not load tasks:\n{exc}")
            return []

    @staticmethod
    def save(tasks: list[Task]) -> None:
        """Persist tasks to the JSON file."""
        try:
            with open(DATA_FILE, "w", encoding="utf-8") as f:
                json.dump([t.to_dict() for t in tasks], f, indent=2, ensure_ascii=False)
        except OSError as exc:
            messagebox.showerror("Save Error", f"Could not save tasks:\n{exc}")


# ──────────────────────────────────────────────────────────────
# Animated Button Helper
# ──────────────────────────────────────────────────────────────
class AnimatedButton(tk.Button):
    """A tk.Button with colour-hover animation."""

    def __init__(self, parent, normal_color: str, hover_color: str, **kwargs):
        super().__init__(parent, bg=normal_color, activebackground=hover_color,
                         relief="flat", cursor="hand2", **kwargs)
        self._normal = normal_color
        self._hover  = hover_color
        self.bind("<Enter>", lambda _: self.config(bg=self._hover))
        self.bind("<Leave>", lambda _: self.config(bg=self._normal))

    def update_colors(self, normal: str, hover: str) -> None:
        self._normal = normal
        self._hover  = hover
        self.config(bg=normal, activebackground=hover)


# ──────────────────────────────────────────────────────────────
# Add / Edit Task Dialog
# ──────────────────────────────────────────────────────────────
class TaskDialog(tk.Toplevel):
    """Modal dialog for creating or editing a task."""

    def __init__(self, parent, theme: dict, task: Task | None = None):
        super().__init__(parent)
        self.theme  = theme
        self.result = None          # set to Task on confirm

        self.title("Edit Task" if task else "New Task")
        self.transient(parent)      # keep dialog attached to parent
        self.resizable(False, False)
        self.configure(bg=theme["bg"])

        self._build(task)
        self.update_idletasks()

        # Centre over parent
        px = parent.winfo_x() + (parent.winfo_width()  - self.winfo_width())  // 2
        py = parent.winfo_y() + (parent.winfo_height() - self.winfo_height()) // 2
        self.geometry(f"+{px}+{py}")

        # Grab input focus AFTER geometry is set
        self.grab_set()
        self.focus_set()

    # ── UI Construction ────────────────────────────────────────
    def _build(self, task: Task | None) -> None:
        pad = {"padx": 20, "pady": 8}

        # ── Title ──
        tk.Label(self, text="Task Title *", font=("Segoe UI", 10, "bold"),
                 bg=self.theme["bg"], fg=self.theme["text"]).pack(anchor="w", **pad)

        self.title_var = tk.StringVar(value=task.title if task else "")
        title_entry = tk.Entry(self, textvariable=self.title_var,
                               font=("Segoe UI", 12),
                               bg=self.theme["entry_bg"], fg=self.theme["entry_fg"],
                               insertbackground=self.theme["text"],
                               relief="flat", bd=6, width=40)
        title_entry.pack(fill="x", padx=20, pady=(0, 4))
        title_entry.focus_set()

        # ── Priority ──
        tk.Label(self, text="Priority", font=("Segoe UI", 10, "bold"),
                 bg=self.theme["bg"], fg=self.theme["text"]).pack(anchor="w", **pad)

        self.priority_var = tk.StringVar(value=task.priority if task else "Medium")
        prio_frame = tk.Frame(self, bg=self.theme["bg"])
        prio_frame.pack(fill="x", padx=20, pady=(0, 8))
        for level in ("High", "Medium", "Low"):
            color = PRIORITY_COLORS[level]
            rb = tk.Radiobutton(prio_frame, text=level,
                                variable=self.priority_var, value=level,
                                bg=self.theme["bg"], fg=color,
                                selectcolor=self.theme["surface"],
                                activebackground=self.theme["bg"],
                                activeforeground=color,
                                font=("Segoe UI", 10, "bold"),
                                bd=0, cursor="hand2")
            rb.pack(side="left", padx=12)

        # ── Due Date ──
        tk.Label(self, text="Due Date (optional)", font=("Segoe UI", 10, "bold"),
                 bg=self.theme["bg"], fg=self.theme["text"]).pack(anchor="w", **pad)

        date_frame = tk.Frame(self, bg=self.theme["bg"])
        date_frame.pack(fill="x", padx=20, pady=(0, 12))

        self.due_var = tk.StringVar(value=task.due_date if task else "")

        if HAS_CALENDAR:
            self._cal_entry = DateEntry(date_frame,
                                        textvariable=self.due_var,
                                        date_pattern="yyyy-mm-dd",
                                        font=("Segoe UI", 10),
                                        background=self.theme["accent"],
                                        foreground=self.theme["btn_fg"],
                                        borderwidth=0,
                                        width=16)
            self._cal_entry.pack(side="left")
            # If editing, set date
            if task and task.due_date:
                try:
                    d = datetime.strptime(task.due_date, "%Y-%m-%d").date()
                    self._cal_entry.set_date(d)
                except ValueError:
                    pass
            tk.Button(date_frame, text="✕ Clear",
                      font=("Segoe UI", 9), bg=self.theme["surface2"],
                      fg=self.theme["text"], relief="flat", cursor="hand2",
                      command=lambda: self.due_var.set("")).pack(side="left", padx=8)
        else:
            # Plain text fallback
            due_entry = tk.Entry(date_frame, textvariable=self.due_var,
                                 font=("Segoe UI", 10),
                                 bg=self.theme["entry_bg"], fg=self.theme["entry_fg"],
                                 insertbackground=self.theme["text"],
                                 relief="flat", bd=6, width=16)
            due_entry.pack(side="left")
            tk.Label(date_frame, text="YYYY-MM-DD",
                     font=("Segoe UI", 8), bg=self.theme["bg"],
                     fg=self.theme["subtext"]).pack(side="left", padx=6)

        # ── Buttons ──
        btn_frame = tk.Frame(self, bg=self.theme["bg"])
        btn_frame.pack(fill="x", padx=20, pady=(8, 20))

        AnimatedButton(btn_frame, self.theme["accent"], self.theme["accent_hover"],
                       text="  Save  ", font=("Segoe UI", 10, "bold"),
                       fg=self.theme["btn_fg"],
                       command=self._confirm).pack(side="right", padx=4)

        AnimatedButton(btn_frame, self.theme["surface2"], self.theme["border"],
                       text="Cancel", font=("Segoe UI", 10),
                       fg=self.theme["text"],
                       command=self._cancel).pack(side="right", padx=4)

    # ── Cancel ─────────────────────────────────────────────────
    def _cancel(self) -> None:
        self.grab_release()
        self.destroy()

    # ── Validation & Result ────────────────────────────────────
    def _confirm(self) -> None:
        title = self.title_var.get().strip()
        if not title:
            messagebox.showwarning("Validation", "Task title cannot be empty.", parent=self)
            return

        due = self.due_var.get().strip()
        # Validate date format if provided
        if due:
            try:
                datetime.strptime(due, "%Y-%m-%d")
            except ValueError:
                messagebox.showwarning("Validation",
                                       "Use YYYY-MM-DD format for the due date.", parent=self)
                return

        self.result = {
            "title":    title,
            "priority": self.priority_var.get(),
            "due_date": due,
        }
        # Release grab before destroying so the main window stays responsive
        self.grab_release()
        self.destroy()


# ──────────────────────────────────────────────────────────────
# Main Application
# ──────────────────────────────────────────────────────────────
class TodoApp:
    """Main application window and controller."""

    def __init__(self, root: tk.Tk):
        self.root       = root
        self.tasks: list[Task] = []
        self._next_id   = 1
        self._theme_key = "dark"
        self._search_var = tk.StringVar()
        self._filter_var = tk.StringVar(value="All")

        self.root.title("✅  Advanced To-Do")
        self.root.geometry("820x680")
        self.root.minsize(700, 560)

        self._load_tasks()
        self._build_ui()
        self._refresh_list()

        # Bind search
        self._search_var.trace_add("write", lambda *_: self._refresh_list())
        self._filter_var.trace_add("write", lambda *_: self._refresh_list())

    # ── Properties ────────────────────────────────────────────
    @property
    def T(self) -> dict:
        """Shorthand for the current theme dictionary."""
        return THEMES[self._theme_key]

    # ── Persistence ───────────────────────────────────────────
    def _load_tasks(self) -> None:
        self.tasks = TaskStorage.load()
        self._next_id = max((t.task_id for t in self.tasks), default=0) + 1

    def _save(self) -> None:
        TaskStorage.save(self.tasks)

    # ── UI Build ──────────────────────────────────────────────
    def _build_ui(self) -> None:
        t = self.T
        self.root.configure(bg=t["bg"])
        self._build_header()
        self._build_search_bar()
        self._build_task_list()
        self._build_action_bar()
        self._build_status_bar()

    def _build_header(self) -> None:
        t = self.T
        self.header_frame = tk.Frame(self.root, bg=t["surface"], height=64)
        self.header_frame.pack(fill="x")
        self.header_frame.pack_propagate(False)

        self.app_title_lbl = tk.Label(
            self.header_frame,
            text="✅  My Advanced To-Do",
            font=("Segoe UI", 18, "bold"),
            bg=t["surface"], fg=t["accent"],
        )
        self.app_title_lbl.pack(side="left", padx=24, pady=12)

        # Theme toggle
        self.theme_btn = AnimatedButton(
            self.header_frame,
            normal_color=t["surface2"],
            hover_color=t["accent"],
            text="☀ Light" if self._theme_key == "dark" else "🌙 Dark",
            font=("Segoe UI", 10),
            fg=t["text"],
            command=self._toggle_theme,
        )
        self.theme_btn.pack(side="right", padx=16, pady=16)

        # Stats label
        self.stats_lbl = tk.Label(
            self.header_frame,
            text="",
            font=("Segoe UI", 9),
            bg=t["surface"], fg=t["subtext"],
        )
        self.stats_lbl.pack(side="right", padx=4, pady=16)

    def _build_search_bar(self) -> None:
        t = self.T
        self.search_frame = tk.Frame(self.root, bg=t["bg"], pady=10)
        self.search_frame.pack(fill="x", padx=20)

        # Search entry
        search_wrapper = tk.Frame(self.search_frame, bg=t["surface"],
                                  bd=0, highlightthickness=1,
                                  highlightbackground=t["border"])
        search_wrapper.pack(side="left", fill="x", expand=True)

        tk.Label(search_wrapper, text="🔍", bg=t["surface"],
                 fg=t["subtext"], font=("Segoe UI", 11)).pack(side="left", padx=8)

        self.search_entry = tk.Entry(
            search_wrapper, textvariable=self._search_var,
            font=("Segoe UI", 11),
            bg=t["surface"], fg=t["text"],
            insertbackground=t["text"], relief="flat", bd=4,
        )
        self.search_entry.pack(side="left", fill="x", expand=True)
        self.search_entry.insert(0, "")

        # Filter buttons
        filter_frame = tk.Frame(self.search_frame, bg=t["bg"])
        filter_frame.pack(side="left", padx=(12, 0))

        self.filter_btns: dict[str, tk.Button] = {}
        for label in ("All", "Active", "Done", "High", "Medium", "Low"):
            btn = tk.Button(
                filter_frame, text=label,
                font=("Segoe UI", 9),
                relief="flat", cursor="hand2",
                command=lambda l=label: self._set_filter(l),
            )
            btn.pack(side="left", padx=2)
            self.filter_btns[label] = btn

        self._update_filter_buttons()

    def _build_task_list(self) -> None:
        t = self.T
        list_frame = tk.Frame(self.root, bg=t["bg"])
        list_frame.pack(fill="both", expand=True, padx=20, pady=(0, 4))

        # Canvas + scrollbar for custom task cards
        self.canvas = tk.Canvas(list_frame, bg=t["bg"],
                                highlightthickness=0, bd=0)
        scrollbar = ttk.Scrollbar(list_frame, orient="vertical",
                                  command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=scrollbar.set)

        scrollbar.pack(side="right", fill="y")
        self.canvas.pack(side="left", fill="both", expand=True)

        self.card_container = tk.Frame(self.canvas, bg=t["bg"])
        self._container_window = self.canvas.create_window(
            (0, 0), window=self.card_container, anchor="nw"
        )

        self.card_container.bind("<Configure>", self._on_frame_configure)
        self.canvas.bind("<Configure>",         self._on_canvas_configure)
        self.canvas.bind("<MouseWheel>",        self._on_mousewheel)

    def _build_action_bar(self) -> None:
        t = self.T
        self.action_frame = tk.Frame(self.root, bg=t["surface"], pady=12)
        self.action_frame.pack(fill="x", side="bottom")

        self.add_btn = AnimatedButton(
            self.action_frame,
            normal_color=t["accent"],
            hover_color=t["accent_hover"],
            text="  ＋  Add Task  ",
            font=("Segoe UI", 11, "bold"),
            fg=t["btn_fg"],
            command=self._add_task,
        )
        self.add_btn.pack(side="left", padx=20)

        # Quick-add entry
        self.quick_var = tk.StringVar()
        self.quick_entry = tk.Entry(
            self.action_frame,
            textvariable=self.quick_var,
            font=("Segoe UI", 11),
            bg=t["entry_bg"], fg=t["entry_fg"],
            insertbackground=t["text"],
            relief="flat", bd=6, width=32,
        )
        self.quick_entry.pack(side="left", ipady=4)
        self.quick_entry.bind("<Return>", self._quick_add)

        tk.Label(self.action_frame,
                 text="← press Enter to quick-add",
                 font=("Segoe UI", 8), bg=t["surface"], fg=t["subtext"]
                 ).pack(side="left", padx=6)

        # ── Explicit Save button ──
        self.save_btn = AnimatedButton(
            self.action_frame,
            normal_color="#0ea5e9",
            hover_color="#38bdf8",
            text="  💾 Save All  ",
            font=("Segoe UI", 10, "bold"),
            fg=t["btn_fg"],
            command=self._manual_save,
        )
        self.save_btn.pack(side="right", padx=20)

    def _build_status_bar(self) -> None:
        t = self.T
        self.status_frame = tk.Frame(self.root, bg=t["surface2"], height=22)
        self.status_frame.pack(fill="x", side="bottom")
        self.status_frame.pack_propagate(False)

        self.status_lbl = tk.Label(
            self.status_frame, text="Ready",
            font=("Segoe UI", 8), bg=t["surface2"], fg=t["subtext"],
        )
        self.status_lbl.pack(side="left", padx=10)

        self.clock_lbl = tk.Label(
            self.status_frame, text="",
            font=("Segoe UI", 8), bg=t["surface2"], fg=t["subtext"],
        )
        self.clock_lbl.pack(side="right", padx=10)
        self._tick_clock()

    # ── Canvas helpers ────────────────────────────────────────
    def _on_frame_configure(self, _event=None) -> None:
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def _on_canvas_configure(self, event) -> None:
        self.canvas.itemconfig(self._container_window, width=event.width)

    def _on_mousewheel(self, event) -> None:
        self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    # ── Clock ─────────────────────────────────────────────────
    def _tick_clock(self) -> None:
        now = datetime.now().strftime("%a, %d %b %Y  %I:%M %p")
        self.clock_lbl.config(text=now)
        self.root.after(30_000, self._tick_clock)

    # ── Theme ─────────────────────────────────────────────────
    def _toggle_theme(self) -> None:
        self._theme_key = "light" if self._theme_key == "dark" else "dark"
        self._apply_theme()

    def _apply_theme(self) -> None:
        t = self.T
        self.root.configure(bg=t["bg"])

        # Header
        self.header_frame.config(bg=t["surface"])
        self.app_title_lbl.config(bg=t["surface"], fg=t["accent"])
        self.stats_lbl.config(bg=t["surface"], fg=t["subtext"])
        self.theme_btn.update_colors(t["surface2"], t["accent"])
        self.theme_btn.config(text="☀ Light" if self._theme_key == "dark" else "🌙 Dark",
                              fg=t["text"])

        # Search bar
        self.search_frame.config(bg=t["bg"])

        # Action bar
        self.action_frame.config(bg=t["surface"])
        self.add_btn.update_colors(t["accent"], t["accent_hover"])
        self.quick_entry.config(bg=t["entry_bg"], fg=t["entry_fg"],
                                insertbackground=t["text"])

        # Status
        self.status_frame.config(bg=t["surface2"])
        self.status_lbl.config(bg=t["surface2"], fg=t["subtext"])
        self.clock_lbl.config(bg=t["surface2"], fg=t["subtext"])

        # Canvas
        self.canvas.config(bg=t["bg"])
        self.card_container.config(bg=t["bg"])

        self._update_filter_buttons()
        self._refresh_list()

    # ── Filter Buttons ────────────────────────────────────────
    def _set_filter(self, label: str) -> None:
        self._filter_var.set(label)
        self._update_filter_buttons()

    def _update_filter_buttons(self) -> None:
        t = self.T
        active = self._filter_var.get()
        for label, btn in self.filter_btns.items():
            if label == active:
                btn.config(bg=t["accent"], fg=t["btn_fg"])
            else:
                btn.config(bg=t["surface2"], fg=t["subtext"])

    # ── Task Filtering ────────────────────────────────────────
    def _visible_tasks(self) -> list[Task]:
        query  = self._search_var.get().strip().lower()
        flt    = self._filter_var.get()
        result = []
        for task in self.tasks:
            # Filter
            if flt == "Active"  and task.completed:     continue
            if flt == "Done"    and not task.completed: continue
            if flt in ("High", "Medium", "Low") and task.priority != flt: continue
            # Search
            if query and query not in task.title.lower(): continue
            result.append(task)
        return result

    # ── List Rendering ────────────────────────────────────────
    def _refresh_list(self) -> None:
        # Clear existing cards
        for widget in self.card_container.winfo_children():
            widget.destroy()

        visible = self._visible_tasks()

        if not visible:
            tk.Label(
                self.card_container,
                text="No tasks found 🎉" if self.tasks else "No tasks yet — add one below!",
                font=("Segoe UI", 14),
                bg=self.T["bg"], fg=self.T["subtext"],
            ).pack(expand=True, pady=60)
        else:
            for task in visible:
                self._render_card(task)

        # Update stats
        total     = len(self.tasks)
        done      = sum(1 for t in self.tasks if t.completed)
        self.stats_lbl.config(text=f"{done}/{total} complete")

        # Status bar
        self.status_lbl.config(text=f"Showing {len(visible)} of {total} tasks")

    def _render_card(self, task: Task) -> None:
        """Build a single task card widget."""
        t      = self.T
        pcolor = PRIORITY_COLORS[task.priority]

        # Card frame
        card = tk.Frame(self.card_container,
                        bg=t["surface"], bd=0,
                        highlightthickness=1,
                        highlightbackground=t["border"])
        card.pack(fill="x", padx=4, pady=4, ipady=6)

        # Priority stripe
        stripe = tk.Frame(card, bg=pcolor, width=5)
        stripe.pack(side="left", fill="y")

        # Left: checkbox + text
        left = tk.Frame(card, bg=t["surface"])
        left.pack(side="left", fill="both", expand=True, padx=10, pady=4)

        # Checkbox (done toggle)
        chk_var = tk.BooleanVar(value=task.completed)
        chk = tk.Checkbutton(
            left, variable=chk_var,
            bg=t["surface"], activebackground=t["surface"],
            selectcolor=t["surface"],
            command=lambda tid=task.task_id, var=chk_var: self._toggle_complete(tid, var),
            cursor="hand2",
        )
        chk.pack(side="left")

        # Title
        title_fg = t["done_fg"] if task.completed else t["text"]
        title_font = ("Segoe UI", 12, "overstrike") if task.completed else ("Segoe UI", 12)
        title_lbl = tk.Label(
            left, text=task.title,
            font=title_font, bg=t["surface"], fg=title_fg,
            anchor="w",
        )
        title_lbl.pack(side="left", fill="x", expand=True)

        # Meta row
        meta_frame = tk.Frame(left, bg=t["surface"])
        meta_frame.pack(side="left")

        # Priority badge
        badge = tk.Label(
            meta_frame, text=f" {task.priority} ",
            font=("Segoe UI", 8, "bold"),
            bg=pcolor, fg="#ffffff", padx=4, pady=1,
        )
        badge.pack(side="left", padx=(0, 6))

        # Due date
        if task.due_date:
            try:
                due_d   = datetime.strptime(task.due_date, "%Y-%m-%d").date()
                overdue = (not task.completed) and (due_d < date.today())
                due_color = "#ef4444" if overdue else t["subtext"]
                due_icon  = "⚠" if overdue else "📅"
            except ValueError:
                due_color = t["subtext"]
                due_icon  = "📅"

            tk.Label(
                meta_frame,
                text=f"{due_icon} {task.due_date}",
                font=("Segoe UI", 8),
                bg=t["surface"], fg=due_color,
            ).pack(side="left", padx=(0, 6))

        # Created at
        tk.Label(
            meta_frame,
            text=f"🕒 {task.created_at}",
            font=("Segoe UI", 8),
            bg=t["surface"], fg=t["subtext"],
        ).pack(side="left")

        # Right: action buttons
        btn_frame = tk.Frame(card, bg=t["surface"])
        btn_frame.pack(side="right", padx=10)

        AnimatedButton(
            btn_frame,
            normal_color=t["edit_bg"],
            hover_color=t["edit_hover"],
            text="✏",
            font=("Segoe UI", 10),
            fg=t["btn_fg"],
            width=2,
            command=lambda tid=task.task_id: self._edit_task(tid),
        ).pack(side="left", padx=2)

        AnimatedButton(
            btn_frame,
            normal_color=t["delete_bg"],
            hover_color=t["delete_hover"],
            text="🗑",
            font=("Segoe UI", 10),
            fg=t["btn_fg"],
            width=2,
            command=lambda tid=task.task_id: self._delete_task(tid),
        ).pack(side="left", padx=2)

    # ── CRUD Operations ───────────────────────────────────────
    def _add_task(self) -> None:
        """Open the add-task dialog."""
        dlg = TaskDialog(self.root, self.T)
        self.root.wait_window(dlg)
        if dlg.result:
            task = Task(
                task_id  = self._next_id,
                title    = dlg.result["title"],
                priority = dlg.result["priority"],
                due_date = dlg.result["due_date"],
            )
            self._next_id += 1
            self.tasks.append(task)
            self._save()
            self._refresh_list()
            self._set_status(f"Task '{task.title}' added.")

    def _quick_add(self, _event=None) -> None:
        """Add a task directly from the quick-add entry."""
        title = self.quick_var.get().strip()
        if not title:
            return
        task = Task(task_id=self._next_id, title=title)
        self._next_id += 1
        self.tasks.append(task)
        self._save()
        self.quick_var.set("")
        self._refresh_list()
        self._set_status(f"Quick-added: '{task.title}'")

    def _manual_save(self) -> None:
        """Explicit save triggered by the Save All button."""
        self._save()
        # Flash the button green to give visual confirmation
        self.save_btn.config(bg="#22c55e", text="  ✅ Saved!  ")
        self.root.after(1500, lambda: self.save_btn.config(
            bg="#0ea5e9", text="  💾 Save All  "
        ))
        self._set_status(f"All {len(self.tasks)} task(s) saved to {DATA_FILE}")

    def _edit_task(self, task_id: int) -> None:
        """Open the edit dialog for an existing task."""
        task = self._find(task_id)
        if not task:
            return
        dlg = TaskDialog(self.root, self.T, task=task)
        self.root.wait_window(dlg)
        if dlg.result:
            task.title    = dlg.result["title"]
            task.priority = dlg.result["priority"]
            task.due_date = dlg.result["due_date"]
            self._save()
            self._refresh_list()
            self._set_status(f"Task '{task.title}' updated.")

    def _delete_task(self, task_id: int) -> None:
        """Delete a task after confirmation."""
        task = self._find(task_id)
        if not task:
            return
        ok = messagebox.askyesno(
            "Delete Task",
            f"Are you sure you want to delete:\n\n'{task.title}'?",
            parent=self.root,
        )
        if ok:
            self.tasks = [t for t in self.tasks if t.task_id != task_id]
            self._save()
            self._refresh_list()
            self._set_status(f"Deleted: '{task.title}'")

    def _toggle_complete(self, task_id: int, var: tk.BooleanVar) -> None:
        """Toggle the completion state of a task."""
        task = self._find(task_id)
        if task:
            task.completed = var.get()
            self._save()
            self._refresh_list()
            state = "completed" if task.completed else "reopened"
            self._set_status(f"Task '{task.title}' {state}.")

    # ── Helpers ───────────────────────────────────────────────
    def _find(self, task_id: int) -> Task | None:
        return next((t for t in self.tasks if t.task_id == task_id), None)

    def _set_status(self, msg: str) -> None:
        self.status_lbl.config(text=msg)
        self.root.after(4000, lambda: self.status_lbl.config(
            text=f"Showing {len(self._visible_tasks())} of {len(self.tasks)} tasks"
        ))


# ──────────────────────────────────────────────────────────────
# Entry Point
# ──────────────────────────────────────────────────────────────
def main() -> None:
    root = tk.Tk()

    # Load a nice font stack (Segoe UI is native on Windows)
    root.option_add("*Font", ("Segoe UI", 10))

    # DPI awareness (Windows)
    try:
        from ctypes import windll
        windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        pass

    # Window icon fallback
    try:
        root.iconbitmap(default="")
    except Exception:
        pass

    app = TodoApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()