#!/usr/bin/env python3
"""
REMEMBER TO FORGET // WORKDAY LOGGER
Standalone Python app — stdlib only (tkinter).
Run with: python workday_logger.py
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog, simpledialog
from datetime import datetime


# ─── COLOUR PALETTE ──────────────────────────────────────────────────────────
BG_DARK    = "#0a0a0f"
BG_PANEL   = "#12121a"
BG_ELEV    = "#1a1a25"
NEON_PINK  = "#ff00ff"
NEON_CYAN  = "#00ffff"
NEON_LIME  = "#39ff14"
NEON_YELL  = "#ffff00"
NEON_RED   = "#ff0033"
NEON_ORNG  = "#ff8800"
NEON_PURP  = "#bf00ff"
TEXT_DIM   = "#888899"
TEXT_MAIN  = "#e0e0e0"

FONT_MONO  = ("Courier", 11)
FONT_MONO_SM = ("Courier", 9)
FONT_BIG   = ("Courier", 13, "bold")

# ─── DEFAULT CATEGORIES ───────────────────────────────────────────────────────
DEFAULT_CATS = [
    "General", "Admin", "Personal", "Creative", "Family",
    "Errands", "Chores", "Learning", "Research",
    "Work", "Ad-Hoc", "Uncategorised", "Miscellaneous", "Surplus to Requirements",
]


def fmt_date(dt: datetime) -> str:
    days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    return f"{dt.strftime('%Y-%m-%d')} - {days[dt.weekday()]}"


def fmt_time(dt: datetime) -> str:
    return dt.strftime("%H:%M")


def today_key() -> str:
    return datetime.now().strftime("%Y-%m-%d")


def calc_hours(start: datetime, end: datetime) -> float:
    diff = (end - start).total_seconds() / 3600
    return round(diff * 2) / 2


# ─── MAIN APP ─────────────────────────────────────────────────────────────────
class WorkdayLogger(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("REMEMBER TO FORGET // WORKLOG")
        self.configure(bg=BG_DARK)
        self.minsize(750, 620)

        # State
        self.current_task = None          # dict or None
        self.days: list[dict] = []        # [{ key, date, lines:[] }]
        self.active_day_idx = 0
        self.custom_cats: list[str] = []

        self._build_ui()
        self._ensure_today()
        self._refresh_log()

    # ── UI CONSTRUCTION ────────────────────────────────────────────────────────
    def _build_ui(self):
        self.rowconfigure(0, weight=1)
        self.columnconfigure(0, weight=1)

        root_frame = tk.Frame(self, bg=BG_DARK, padx=16, pady=16)
        root_frame.grid(row=0, column=0, sticky="nsew")
        root_frame.columnconfigure(0, weight=1)

        # HEADER
        hdr = tk.Frame(root_frame, bg=BG_PANEL, padx=12, pady=10,
                       highlightbackground=NEON_PINK, highlightthickness=2)
        hdr.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        tk.Label(hdr, text="WORKDAY LOGBOOK", font=("Courier", 22, "bold"),
                 fg=NEON_PINK, bg=BG_PANEL).pack()
        tk.Label(hdr, text="FORGETFUL TASK TRACKER // NO DATA STORED",
                 font=FONT_MONO_SM, fg=NEON_CYAN, bg=BG_PANEL).pack()

        # IDENTITY FIELDS
        id_frame = tk.Frame(root_frame, bg=BG_DARK)
        id_frame.grid(row=1, column=0, sticky="ew", pady=(0, 8))
        id_frame.columnconfigure(1, weight=1)
        id_frame.columnconfigure(3, weight=1)

        tk.Label(id_frame, text="OPERATOR:", font=FONT_MONO_SM,
                 fg=NEON_CYAN, bg=BG_DARK).grid(row=0, column=0, sticky="w", padx=(0,6))
        self.var_name = tk.StringVar()
        tk.Entry(id_frame, textvariable=self.var_name, font=FONT_MONO,
                 bg=BG_ELEV, fg="white", insertbackground="white",
                 relief="flat", highlightbackground=NEON_CYAN,
                 highlightthickness=1).grid(row=0, column=1, sticky="ew")

        tk.Label(id_frame, text="  ORG:", font=FONT_MONO_SM,
                 fg=NEON_CYAN, bg=BG_DARK).grid(row=0, column=2, sticky="w", padx=(10,6))
        self.var_org = tk.StringVar()
        tk.Entry(id_frame, textvariable=self.var_org, font=FONT_MONO,
                 bg=BG_ELEV, fg="white", insertbackground="white",
                 relief="flat", highlightbackground=NEON_CYAN,
                 highlightthickness=1).grid(row=0, column=3, sticky="ew")

        # BUTTONS
        btn_frame = tk.Frame(root_frame, bg=BG_DARK)
        btn_frame.grid(row=2, column=0, sticky="ew", pady=(0, 8))
        for col in range(4):
            btn_frame.columnconfigure(col, weight=1)

        def styled_btn(parent, text, cmd, fg, **kwargs):
            b = tk.Button(parent, text=text, command=cmd, font=("Courier", 12, "bold"),
                          fg=fg, bg=BG_PANEL, activeforeground="white",
                          activebackground=BG_ELEV, relief="flat",
                          highlightbackground=fg, highlightthickness=2,
                          padx=10, pady=8, cursor="hand2", **kwargs)
            return b

        styled_btn(btn_frame, "> START TASK <", self._on_start, NEON_LIME)\
            .grid(row=0, column=0, padx=4, sticky="ew")
        styled_btn(btn_frame, "> END TASK <", self._on_end, NEON_RED)\
            .grid(row=0, column=1, padx=4, sticky="ew")
        styled_btn(btn_frame, "> CATEGORIES <", self._on_cats, NEON_ORNG)\
            .grid(row=0, column=2, padx=4, sticky="ew")
        styled_btn(btn_frame, "> + NEW DAY <", self._on_new_day, NEON_YELL)\
            .grid(row=0, column=3, padx=4, sticky="ew")

        # STATUS BAR
        status_frame = tk.Frame(root_frame, bg=BG_PANEL,
                                highlightbackground=NEON_PURP, highlightthickness=2)
        status_frame.grid(row=3, column=0, sticky="ew", pady=(0, 8))
        status_frame.columnconfigure(1, weight=1)

        self.lbl_status_dot = tk.Label(status_frame, text="●", font=("Courier", 14),
                                        fg=NEON_YELL, bg=BG_PANEL, padx=8)
        self.lbl_status_dot.grid(row=0, column=0)
        self.lbl_status = tk.Label(status_frame, text="IDLE", font=FONT_MONO_SM,
                                    fg=NEON_YELL, bg=BG_PANEL)
        self.lbl_status.grid(row=0, column=1, sticky="w")
        self.lbl_current = tk.Label(status_frame, text="", font=FONT_MONO_SM,
                                     fg=NEON_CYAN, bg=BG_PANEL, padx=8)
        self.lbl_current.grid(row=0, column=2, sticky="e")

        # OUTPUT
        out_frame = tk.Frame(root_frame, bg=BG_PANEL,
                             highlightbackground=NEON_PINK, highlightthickness=2)
        out_frame.grid(row=4, column=0, sticky="nsew", pady=(0, 8))
        out_frame.columnconfigure(0, weight=1)
        out_frame.rowconfigure(1, weight=1)
        root_frame.rowconfigure(4, weight=1)

        out_hdr = tk.Frame(out_frame, bg=BG_PANEL)
        out_hdr.grid(row=0, column=0, sticky="ew", padx=8, pady=(6, 2))
        tk.Label(out_hdr, text="// WORK LOG OUTPUT", font=FONT_BIG,
                 fg=NEON_PINK, bg=BG_PANEL).pack(side="left")

        btn_area = tk.Frame(out_hdr, bg=BG_PANEL)
        btn_area.pack(side="right")

        def small_btn(text, cmd, fg):
            return tk.Button(btn_area, text=text, command=cmd, font=FONT_MONO_SM,
                             fg=fg, bg=BG_PANEL, relief="flat",
                             highlightbackground=fg, highlightthickness=1,
                             padx=6, pady=3, cursor="hand2")

        small_btn("Copy", self._on_copy, NEON_CYAN).pack(side="left", padx=3)
        small_btn("Export .md", self._on_export, NEON_LIME).pack(side="left", padx=3)

        self.txt_output = tk.Text(out_frame, font=FONT_MONO,
                                   bg=BG_ELEV, fg=TEXT_MAIN,
                                   insertbackground=NEON_CYAN,
                                   relief="flat", padx=10, pady=10,
                                   state="disabled", wrap="none",
                                   highlightthickness=0)
        self.txt_output.grid(row=1, column=0, sticky="nsew", padx=2, pady=2)

        scroll_y = tk.Scrollbar(out_frame, command=self.txt_output.yview,
                                 bg=BG_DARK, troughcolor=BG_ELEV)
        scroll_y.grid(row=1, column=1, sticky="ns")
        scroll_x = tk.Scrollbar(out_frame, orient="horizontal",
                                 command=self.txt_output.xview,
                                 bg=BG_DARK, troughcolor=BG_ELEV)
        scroll_x.grid(row=2, column=0, sticky="ew")
        self.txt_output.configure(yscrollcommand=scroll_y.set,
                                   xscrollcommand=scroll_x.set)

        # FOOTER
        tk.Label(root_frame,
                 text="⚠ DATA IS LOST WHEN APP CLOSES — Export before quitting ⚠",
                 font=FONT_MONO_SM, fg=NEON_YELL, bg=BG_DARK)\
            .grid(row=5, column=0, pady=(4, 0))

    # ── HELPERS ────────────────────────────────────────────────────────────────
    def _ensure_today(self):
        key = today_key()
        for i, d in enumerate(self.days):
            if d["key"] == key:
                self.active_day_idx = i
                return False
        self.days.append({"key": key, "date": fmt_date(datetime.now()), "lines": []})
        self.active_day_idx = len(self.days) - 1
        return True

    def _active_day(self) -> dict:
        return self.days[self.active_day_idx]

    def _all_cats(self) -> list[str]:
        return DEFAULT_CATS + self.custom_cats

    def _set_status(self, active: bool, task_text: str = ""):
        if active:
            self.lbl_status_dot.config(fg=NEON_LIME)
            self.lbl_status.config(text="TASK ACTIVE", fg=NEON_LIME)
            self.lbl_current.config(text=task_text)
        else:
            self.lbl_status_dot.config(fg=NEON_YELL)
            self.lbl_status.config(text="IDLE", fg=NEON_YELL)
            self.lbl_current.config(text="")

    def _refresh_log(self):
        name = self.var_name.get().strip() or "Unknown"
        org  = self.var_org.get().strip()  or "Unknown"
        lines = []
        for idx, day in enumerate(self.days):
            if idx > 0:
                lines.append("\n---\n")
            lines.append(f"{day['date']} - {name} - {org}\n")
            lines.append("\n| BEGIN | TASK/ACTIVITY | END | HRS |\n")
            lines.append("| :-- | :-- | :-- | :-: |\n")
            for ln in day["lines"]:
                lines.append(f"| {ln['start']} | {ln['desc']} | {ln['end']} | {ln['hours']} |\n")
            if idx == self.active_day_idx and self.current_task:
                ct = self.current_task
                lines.append(f"| {ct['start_time']} | {ct['category']} - {ct['desc']} | ... | ... |\n")

        content = "".join(lines)
        self.txt_output.config(state="normal")
        self.txt_output.delete("1.0", "end")
        self.txt_output.insert("1.0", content)
        self.txt_output.config(state="disabled")

    def _get_log_text(self) -> str:
        return self.txt_output.get("1.0", "end-1c")

    # ── ACTIONS ───────────────────────────────────────────────────────────────
    def _on_start(self):
        if not self.var_name.get().strip() or not self.var_org.get().strip():
            messagebox.showwarning("Missing info", "Please enter Name and Organization.")
            return
        self._ensure_today()
        StartTaskDialog(self)

    def _on_end(self):
        if not self.current_task:
            messagebox.showinfo("No Task", "There is no active task to end.")
            return
        EndTaskDialog(self)

    def _on_cats(self):
        CategoriesDialog(self)

    def _on_new_day(self):
        if not self.var_name.get().strip() or not self.var_org.get().strip():
            messagebox.showwarning("Missing info", "Please enter Name and Organization.")
            return
        key = today_key()
        self.days.append({"key": key, "date": fmt_date(datetime.now()), "lines": []})
        self.active_day_idx = len(self.days) - 1
        self.current_task = None
        self._set_status(False)
        self._refresh_log()

    def _on_copy(self):
        text = self._get_log_text()
        self.clipboard_clear()
        self.clipboard_append(text)
        messagebox.showinfo("Copied", "Worklog copied to clipboard.")

    def _on_export(self):
        text = self._get_log_text().strip()
        if not text:
            messagebox.showwarning("Empty", "Nothing to export yet.")
            return
        name = (self.var_name.get().strip() or "worklog").replace(" ", "_")
        default_name = f"worklog_{name}_{today_key()}.md"
        path = filedialog.asksaveasfilename(
            defaultextension=".md",
            filetypes=[("Markdown files", "*.md"), ("Text files", "*.txt"), ("All files", "*.*")],
            initialfile=default_name,
            title="Export Worklog"
        )
        if path:
            with open(path, "w", encoding="utf-8") as f:
                f.write(text)
            messagebox.showinfo("Exported", f"Saved to:\n{path}")


# ─── DIALOGS ──────────────────────────────────────────────────────────────────
class BaseDialog(tk.Toplevel):
    def __init__(self, app: WorkdayLogger, title: str, border_color: str = NEON_PINK):
        super().__init__(app)
        self.app = app
        self.title(title)
        self.configure(bg=BG_PANEL)
        self.resizable(False, False)
        self.grab_set()
        # Border effect via highlight
        self.config(highlightbackground=border_color, highlightthickness=3)
        self.bind("<Escape>", lambda e: self.destroy())
        self._center()

    def _center(self):
        self.update_idletasks()
        w, h = self.winfo_reqwidth(), self.winfo_reqheight()
        x = self.app.winfo_x() + (self.app.winfo_width()  - w) // 2
        y = self.app.winfo_y() + (self.app.winfo_height() - h) // 2
        self.geometry(f"+{x}+{y}")


class StartTaskDialog(BaseDialog):
    def __init__(self, app: WorkdayLogger):
        super().__init__(app, "> START NEW TASK <")
        self.minsize(380, 260)

        frame = tk.Frame(self, bg=BG_PANEL, padx=20, pady=16)
        frame.pack(fill="both", expand=True)

        tk.Label(frame, text="> START NEW TASK <", font=("Courier", 14, "bold"),
                 fg=NEON_PINK, bg=BG_PANEL).pack(pady=(0, 12))

        # Category
        tk.Label(frame, text="CATEGORY:", font=FONT_MONO_SM, fg=NEON_CYAN, bg=BG_PANEL,
                 anchor="w").pack(fill="x")
        self.var_cat = tk.StringVar()
        cats = app._all_cats()
        cat_cb = ttk.Combobox(frame, textvariable=self.var_cat, values=cats,
                               font=FONT_MONO, state="readonly", width=40)
        cat_cb.pack(fill="x", pady=(2, 10))
        self._style_combo(cat_cb)

        # Description
        tk.Label(frame, text="TASK DESCRIPTION:", font=FONT_MONO_SM, fg=NEON_CYAN, bg=BG_PANEL,
                 anchor="w").pack(fill="x")
        self.var_desc = tk.StringVar()
        tk.Entry(frame, textvariable=self.var_desc, font=FONT_MONO,
                 bg=BG_ELEV, fg="white", insertbackground="white",
                 relief="flat", highlightbackground=NEON_CYAN,
                 highlightthickness=1).pack(fill="x", pady=(2, 14))

        # Buttons
        btn_row = tk.Frame(frame, bg=BG_PANEL)
        btn_row.pack(fill="x")
        btn_row.columnconfigure(0, weight=1)
        btn_row.columnconfigure(1, weight=1)

        tk.Button(btn_row, text="> COMMIT <", command=self._commit,
                  font=("Courier", 12, "bold"), fg=NEON_CYAN, bg=BG_PANEL,
                  relief="flat", highlightbackground=NEON_CYAN, highlightthickness=2,
                  pady=6, cursor="hand2").grid(row=0, column=0, padx=(0,4), sticky="ew")
        tk.Button(btn_row, text="> CANCEL <", command=self.destroy,
                  font=("Courier", 12, "bold"), fg=TEXT_DIM, bg=BG_PANEL,
                  relief="flat", highlightbackground=TEXT_DIM, highlightthickness=2,
                  pady=6, cursor="hand2").grid(row=0, column=1, padx=(4,0), sticky="ew")

        cat_cb.focus_set()
        self._center()

    def _style_combo(self, cb):
        style = ttk.Style()
        style.theme_use("default")
        style.configure("TCombobox",
                         fieldbackground=BG_ELEV, background=BG_ELEV,
                         foreground="white", selectforeground="white",
                         selectbackground=BG_ELEV)

    def _commit(self):
        cat  = self.var_cat.get().strip()
        desc = self.var_desc.get().strip()
        if not cat:  messagebox.showwarning("Missing", "Please select a category.", parent=self); return
        if not desc: messagebox.showwarning("Missing", "Please enter a task description.", parent=self); return

        now = datetime.now()
        day = self.app._active_day()

        if self.app.current_task:
            ct = self.app.current_task
            hrs = calc_hours(ct["start_dt"], now)
            day["lines"].append({
                "start": ct["start_time"],
                "desc": f"{ct['category']} - {ct['desc']} (switched at {fmt_time(now)})",
                "end": fmt_time(now),
                "hours": hrs
            })

        self.app.current_task = {
            "start_dt": now,
            "start_time": fmt_time(now),
            "category": cat,
            "desc": desc
        }
        self.app._set_status(True, f"{cat} - {desc}")
        self.app._refresh_log()
        self.destroy()


class EndTaskDialog(BaseDialog):
    def __init__(self, app: WorkdayLogger):
        super().__init__(app, "> END TASK <")
        ct = app.current_task
        self.minsize(340, 260)

        frame = tk.Frame(self, bg=BG_PANEL, padx=20, pady=16)
        frame.pack(fill="both", expand=True)

        tk.Label(frame, text="> END TASK <", font=("Courier", 14, "bold"),
                 fg=NEON_PINK, bg=BG_PANEL).pack(pady=(0, 10))

        now = datetime.now()
        hrs = calc_hours(ct["start_dt"], now)

        def info_row(label, value, color):
            row = tk.Frame(frame, bg=BG_PANEL)
            row.pack(fill="x", pady=2)
            tk.Label(row, text=f"{label}:", font=FONT_MONO_SM, fg=NEON_CYAN, bg=BG_PANEL,
                     width=14, anchor="w").pack(side="left")
            tk.Label(row, text=value, font=FONT_MONO, fg=color, bg=BG_PANEL,
                     anchor="w").pack(side="left")

        info_row("TASK",     f"{ct['category']} - {ct['desc']}", NEON_CYAN)
        info_row("STARTED",  ct["start_time"],                   NEON_LIME)
        info_row("ENDS",     fmt_time(now),                      NEON_RED)
        info_row("DURATION", f"{hrs} hours (to 0.5h)",           NEON_YELL)

        tk.Frame(frame, bg=NEON_PINK, height=1).pack(fill="x", pady=10)

        btn_row = tk.Frame(frame, bg=BG_PANEL)
        btn_row.pack(fill="x")
        btn_row.columnconfigure(0, weight=1)
        btn_row.columnconfigure(1, weight=1)

        tk.Button(btn_row, text="> COMMIT <", command=self._commit,
                  font=("Courier", 12, "bold"), fg=NEON_CYAN, bg=BG_PANEL,
                  relief="flat", highlightbackground=NEON_CYAN, highlightthickness=2,
                  pady=6, cursor="hand2").grid(row=0, column=0, padx=(0,4), sticky="ew")
        tk.Button(btn_row, text="> CANCEL <", command=self.destroy,
                  font=("Courier", 12, "bold"), fg=TEXT_DIM, bg=BG_PANEL,
                  relief="flat", highlightbackground=TEXT_DIM, highlightthickness=2,
                  pady=6, cursor="hand2").grid(row=0, column=1, padx=(4,0), sticky="ew")

        self._now = now
        self._hours = hrs
        self._center()

    def _commit(self):
        ct = self.app.current_task
        self.app._active_day()["lines"].append({
            "start": ct["start_time"],
            "desc": f"{ct['category']} - {ct['desc']}",
            "end": fmt_time(self._now),
            "hours": self._hours
        })
        self.app.current_task = None
        self.app._set_status(False)
        self.app._refresh_log()
        self.destroy()


class CategoriesDialog(BaseDialog):
    def __init__(self, app: WorkdayLogger):
        super().__init__(app, "> CATEGORIES <", border_color=NEON_ORNG)
        self.minsize(360, 420)

        frame = tk.Frame(self, bg=BG_PANEL, padx=16, pady=14)
        frame.pack(fill="both", expand=True)
        frame.rowconfigure(2, weight=1)
        frame.columnconfigure(0, weight=1)

        tk.Label(frame, text="> MANAGE CATEGORIES <", font=("Courier", 13, "bold"),
                 fg=NEON_ORNG, bg=BG_PANEL).grid(row=0, column=0, columnspan=2, pady=(0,10))

        # Add row
        add_frame = tk.Frame(frame, bg=BG_PANEL)
        add_frame.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(0, 8))
        add_frame.columnconfigure(0, weight=1)

        self.var_new = tk.StringVar()
        tk.Entry(add_frame, textvariable=self.var_new, font=FONT_MONO,
                 bg=BG_ELEV, fg="white", insertbackground="white",
                 relief="flat", highlightbackground=NEON_ORNG,
                 highlightthickness=1, width=24).grid(row=0, column=0, sticky="ew", padx=(0,6))
        tk.Button(add_frame, text="+ ADD", command=self._add,
                  font=FONT_MONO_SM, fg=NEON_ORNG, bg=BG_PANEL,
                  relief="flat", highlightbackground=NEON_ORNG, highlightthickness=1,
                  padx=8, pady=4, cursor="hand2").grid(row=0, column=1)

        # List
        listbox_frame = tk.Frame(frame, bg=BG_ELEV,
                                  highlightbackground=NEON_ORNG, highlightthickness=1)
        listbox_frame.grid(row=2, column=0, columnspan=2, sticky="nsew", pady=(0, 8))
        listbox_frame.rowconfigure(0, weight=1)
        listbox_frame.columnconfigure(0, weight=1)

        self.listbox = tk.Listbox(listbox_frame, font=FONT_MONO_SM,
                                   bg=BG_ELEV, fg=TEXT_MAIN,
                                   selectbackground=BG_PANEL,
                                   selectforeground=NEON_ORNG,
                                   relief="flat", highlightthickness=0,
                                   activestyle="none", height=14)
        self.listbox.grid(row=0, column=0, sticky="nsew")
        sb = tk.Scrollbar(listbox_frame, command=self.listbox.yview, bg=BG_DARK)
        sb.grid(row=0, column=1, sticky="ns")
        self.listbox.config(yscrollcommand=sb.set)

        self._populate_list()

        tk.Button(frame, text="[ DELETE SELECTED CUSTOM CAT ]", command=self._delete,
                  font=FONT_MONO_SM, fg=NEON_RED, bg=BG_PANEL,
                  relief="flat", highlightbackground=NEON_RED, highlightthickness=1,
                  pady=4, cursor="hand2").grid(row=3, column=0, columnspan=2, sticky="ew", pady=(0,6))

        tk.Label(frame, text="⚠ Custom categories are session-only",
                 font=FONT_MONO_SM, fg=TEXT_DIM, bg=BG_PANEL)\
            .grid(row=4, column=0, columnspan=2)

        tk.Button(frame, text="> CLOSE <", command=self.destroy,
                  font=("Courier", 12, "bold"), fg=TEXT_DIM, bg=BG_PANEL,
                  relief="flat", highlightbackground=TEXT_DIM, highlightthickness=2,
                  pady=6, cursor="hand2").grid(row=5, column=0, columnspan=2, sticky="ew", pady=(8,0))

        self.var_new.trace_add("write", lambda *_: None)
        self.bind("<Return>", lambda e: self._add())
        self._center()

    def _populate_list(self):
        self.listbox.delete(0, "end")
        for c in DEFAULT_CATS:
            self.listbox.insert("end", f"  {c}  [built-in]")
        for c in self.app.custom_cats:
            self.listbox.insert("end", f"  {c}  [custom]")
            idx = self.listbox.size() - 1
            self.listbox.itemconfig(idx, fg=NEON_ORNG)

    def _add(self):
        val = self.var_new.get().strip().replace(" ", "-")
        if not val:
            return
        all_cats = DEFAULT_CATS + self.app.custom_cats
        if val in all_cats:
            self.var_new.set("")
            return
        self.app.custom_cats.append(val)
        self.var_new.set("")
        self._populate_list()

    def _delete(self):
        sel = self.listbox.curselection()
        if not sel:
            return
        idx = sel[0]
        n_builtin = len(DEFAULT_CATS)
        if idx < n_builtin:
            messagebox.showinfo("Built-in", "Built-in categories cannot be deleted.", parent=self)
            return
        custom_idx = idx - n_builtin
        del self.app.custom_cats[custom_idx]
        self._populate_list()


# ─── ENTRY POINT ─────────────────────────────────────────────────────────────
if __name__ == "__main__":
    app = WorkdayLogger()
    app.mainloop()
