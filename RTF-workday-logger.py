#!/usr/bin/env python3
"""
REMEMBER TO FORGET // WORKDAY LOGGER
Standalone Python app — stdlib only (tkinter).
Run with: python RTF-workday-logger.py
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from datetime import datetime
import os
import sys
import hashlib
import hmac as _hmac
import secrets


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

FONT_MONO    = ("Courier", 11)
FONT_MONO_SM = ("Courier", 9)
FONT_BIG     = ("Courier", 13, "bold")

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


def fmt_ts(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%d %H:%M:%S")


def today_key() -> str:
    return datetime.now().strftime("%Y-%m-%d")


def calc_hours(start: datetime, end: datetime) -> float:
    diff = (end - start).total_seconds() / 3600
    return round(diff * 2) / 2


def script_dir() -> str:
    """Directory of the running script; PyInstaller-aware."""
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(sys.argv[0]))


def compute_file_hmac(full_key: str, auditor: str,
                      auditor_org: str, created: str) -> str:
    """HMAC-SHA256 over header identity fields, keyed with the full split key."""
    msg = f"{auditor}{auditor_org}{created}".encode()
    return _hmac.new(full_key.encode(), msg, hashlib.sha256).hexdigest()[:32]


# ─── MAIN APP ─────────────────────────────────────────────────────────────────
class WorkdayLogger(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("REMEMBER TO FORGET // WORKLOG")
        self.configure(bg=BG_DARK)
        self.minsize(750, 680)

        # Core state
        self.open_ts          = datetime.now()
        self.current_task     = None
        self.days: list[dict] = []
        self.active_day_idx   = 0
        self.custom_cats: list[str] = []

        # Journal state: {"text": str, "timestamp": datetime|None, "locked": bool}
        self.journal_morning   = {"text": "", "timestamp": None, "locked": False}
        self.journal_afternoon = {"text": "", "timestamp": None, "locked": False}

        # Hashbrowns consent: None = not yet asked, True = yes, False = no
        self.hashbrowns_consent: bool | None = None

        # Track whether the log has been downloaded this session
        self.exported = False

        self._build_ui()
        self.protocol("WM_DELETE_WINDOW", self._on_close)
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
                 fg=NEON_CYAN, bg=BG_DARK).grid(row=0, column=0, sticky="w", padx=(0, 6))
        self.var_name = tk.StringVar()
        tk.Entry(id_frame, textvariable=self.var_name, font=FONT_MONO,
                 bg=BG_ELEV, fg="white", insertbackground="white",
                 relief="flat", highlightbackground=NEON_CYAN,
                 highlightthickness=1).grid(row=0, column=1, sticky="ew")

        tk.Label(id_frame, text="  ORG:", font=FONT_MONO_SM,
                 fg=NEON_CYAN, bg=BG_DARK).grid(row=0, column=2, sticky="w", padx=(10, 6))
        self.var_org = tk.StringVar()
        tk.Entry(id_frame, textvariable=self.var_org, font=FONT_MONO,
                 bg=BG_ELEV, fg="white", insertbackground="white",
                 relief="flat", highlightbackground=NEON_CYAN,
                 highlightthickness=1).grid(row=0, column=3, sticky="ew")

        # ACTION BUTTONS
        btn_frame = tk.Frame(root_frame, bg=BG_DARK)
        btn_frame.grid(row=2, column=0, sticky="ew", pady=(0, 8))
        for col in range(4):
            btn_frame.columnconfigure(col, weight=1)

        def styled_btn(parent, text, cmd, fg, **kwargs):
            return tk.Button(parent, text=text, command=cmd,
                             font=("Courier", 12, "bold"),
                             fg=fg, bg=BG_PANEL, activeforeground="white",
                             activebackground=BG_ELEV, relief="flat",
                             highlightbackground=fg, highlightthickness=2,
                             padx=10, pady=8, cursor="hand2", **kwargs)

        styled_btn(btn_frame, "> START TASK <",  self._on_start,   NEON_LIME)\
            .grid(row=0, column=0, padx=4, sticky="ew")
        styled_btn(btn_frame, "> END TASK <",    self._on_end,     NEON_RED)\
            .grid(row=0, column=1, padx=4, sticky="ew")
        styled_btn(btn_frame, "> CATEGORIES <",  self._on_cats,    NEON_ORNG)\
            .grid(row=0, column=2, padx=4, sticky="ew")
        styled_btn(btn_frame, "> + NEW DAY <",   self._on_new_day, NEON_YELL)\
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

        # ── NOTEBOOK ──────────────────────────────────────────────────────────
        nb_style = ttk.Style()
        nb_style.theme_use("default")
        nb_style.configure("RTF.TNotebook",
                           background=BG_DARK, borderwidth=0,
                           tabmargins=[0, 0, 0, 0])
        nb_style.configure("RTF.TNotebook.Tab",
                           background=BG_PANEL, foreground=TEXT_DIM,
                           font=("Courier", 11, "bold"), padding=[14, 6],
                           borderwidth=0)
        nb_style.map("RTF.TNotebook.Tab",
                     background=[("selected", BG_ELEV)],
                     foreground=[("selected", NEON_PINK)])

        notebook = ttk.Notebook(root_frame, style="RTF.TNotebook")
        notebook.grid(row=4, column=0, sticky="nsew", pady=(0, 8))
        root_frame.rowconfigure(4, weight=1)

        # ── TAB 1: WORK LOG ───────────────────────────────────────────────────
        log_tab = tk.Frame(notebook, bg=BG_PANEL,
                           highlightbackground=NEON_PINK, highlightthickness=2)
        log_tab.columnconfigure(0, weight=1)
        log_tab.rowconfigure(1, weight=1)
        notebook.add(log_tab, text="  // WORK LOG  ")

        log_hdr = tk.Frame(log_tab, bg=BG_PANEL)
        log_hdr.grid(row=0, column=0, sticky="ew", padx=8, pady=(6, 2))
        tk.Label(log_hdr, text="// WORK LOG OUTPUT", font=FONT_BIG,
                 fg=NEON_PINK, bg=BG_PANEL).pack(side="left")

        btn_area = tk.Frame(log_hdr, bg=BG_PANEL)
        btn_area.pack(side="right")

        def small_btn(parent, text, cmd, fg):
            return tk.Button(parent, text=text, command=cmd, font=FONT_MONO_SM,
                             fg=fg, bg=BG_PANEL, relief="flat",
                             highlightbackground=fg, highlightthickness=1,
                             padx=6, pady=3, cursor="hand2")

        small_btn(btn_area, "Copy .md",     self._on_copy,   NEON_CYAN).pack(side="left", padx=3)
        small_btn(btn_area, "Download .md", self._on_export, NEON_LIME).pack(side="left", padx=3)

        self.txt_output = tk.Text(log_tab, font=FONT_MONO,
                                  bg=BG_ELEV, fg=TEXT_MAIN,
                                  insertbackground=NEON_CYAN,
                                  relief="flat", padx=10, pady=10,
                                  state="disabled", wrap="none",
                                  highlightthickness=0)
        self.txt_output.grid(row=1, column=0, sticky="nsew", padx=2, pady=2)

        scroll_y = tk.Scrollbar(log_tab, command=self.txt_output.yview,
                                bg=BG_DARK, troughcolor=BG_ELEV)
        scroll_y.grid(row=1, column=1, sticky="ns")
        scroll_x = tk.Scrollbar(log_tab, orient="horizontal",
                                command=self.txt_output.xview,
                                bg=BG_DARK, troughcolor=BG_ELEV)
        scroll_x.grid(row=2, column=0, sticky="ew")
        self.txt_output.configure(yscrollcommand=scroll_y.set,
                                  xscrollcommand=scroll_x.set)

        # ── TAB 2: JOURNAL ────────────────────────────────────────────────────
        jnl_tab = tk.Frame(notebook, bg=BG_PANEL,
                           highlightbackground=NEON_PURP, highlightthickness=2)
        jnl_tab.columnconfigure(0, weight=1)
        jnl_tab.rowconfigure(1, weight=1)
        jnl_tab.rowconfigure(4, weight=1)
        notebook.add(jnl_tab, text="  // JOURNAL  ")

        self._build_journal_section(jnl_tab, text_row=1, label="◈ MORNING JOURNAL",
                                    color=NEON_CYAN,  key="morning",   top_row=0)
        tk.Frame(jnl_tab, bg=NEON_PURP, height=1).grid(
            row=3, column=0, columnspan=2, sticky="ew", padx=10, pady=2)
        self._build_journal_section(jnl_tab, text_row=4, label="◈ AFTERNOON JOURNAL",
                                    color=NEON_ORNG, key="afternoon", top_row=3)

        # FOOTER
        tk.Label(root_frame,
                 text="⚠ DATA IS LOST WHEN APP CLOSES — Export before quitting ⚠",
                 font=FONT_MONO_SM, fg=NEON_YELL, bg=BG_DARK)\
            .grid(row=5, column=0, pady=(4, 0))

    def _build_journal_section(self, parent, text_row: int, label: str,
                                color: str, key: str, top_row: int):
        hdr = tk.Frame(parent, bg=BG_PANEL)
        hdr.grid(row=top_row, column=0, columnspan=2, sticky="ew", padx=8, pady=(8, 2))
        hdr.columnconfigure(0, weight=1)

        tk.Label(hdr, text=label, font=FONT_BIG, fg=color, bg=BG_PANEL)\
            .grid(row=0, column=0, sticky="w")

        ts_lbl = tk.Label(hdr, text="", font=FONT_MONO_SM, fg=TEXT_DIM, bg=BG_PANEL)
        ts_lbl.grid(row=0, column=1, padx=(10, 6), sticky="e")

        complete_btn = tk.Button(hdr, text="[ COMPLETE ]",
                                 font=FONT_MONO_SM, fg=color, bg=BG_PANEL,
                                 relief="flat", highlightbackground=color,
                                 highlightthickness=1, padx=8, pady=3, cursor="hand2")
        complete_btn.grid(row=0, column=2, sticky="e")

        txt = tk.Text(parent, font=FONT_MONO,
                      bg=BG_ELEV, fg=TEXT_MAIN, insertbackground=color,
                      relief="flat", padx=8, pady=8, wrap="word",
                      highlightthickness=1, highlightbackground=color, height=6)
        txt.grid(row=text_row, column=0, sticky="nsew", padx=(8, 0), pady=(0, 6))

        sb = tk.Scrollbar(parent, command=txt.yview, bg=BG_DARK, troughcolor=BG_ELEV)
        sb.grid(row=text_row, column=1, sticky="ns", padx=(0, 4), pady=(0, 6))
        txt.configure(yscrollcommand=sb.set)

        def on_complete(t=txt, ts=ts_lbl, k=key, btn=complete_btn, c=color):
            state = getattr(self, f"journal_{k}")
            if state["locked"]:
                return
            content = t.get("1.0", "end-1c").strip()
            if not content:
                messagebox.showwarning("Empty",
                                       f"Nothing to lock in the {k} journal.",
                                       parent=self)
                return
            now = datetime.now()
            state["text"]      = content
            state["timestamp"] = now
            state["locked"]    = True
            t.config(state="disabled", highlightbackground=TEXT_DIM, fg=TEXT_DIM)
            ts.config(text=f"✓  locked {fmt_ts(now)}", fg=c)
            btn.config(text="[ LOCKED ]", fg=TEXT_DIM,
                       highlightbackground=TEXT_DIM, cursor="arrow",
                       activeforeground=TEXT_DIM)

        complete_btn.config(command=on_complete)

        setattr(self, f"_jnl_{key}_txt", txt)
        setattr(self, f"_jnl_{key}_ts",  ts_lbl)
        setattr(self, f"_jnl_{key}_btn", complete_btn)
        setattr(self, f"_jnl_{key}_clr", color)

    # ── HELPERS ────────────────────────────────────────────────────────────────
    def _ensure_today(self):
        key = today_key()
        for i, d in enumerate(self.days):
            if d["key"] == key:
                self.active_day_idx = i
                return False
        self.days.append({
            "key":      key,
            "date":     fmt_date(datetime.now()),
            "lines":    [],
            "journals": {"morning": None, "afternoon": None},
        })
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
                lines.append(
                    f"| {ln['start']} | {ln['desc']} | {ln['end']} | {ln['hours']} |\n")
            if idx == self.active_day_idx and self.current_task:
                ct = self.current_task
                lines.append(
                    f"| {ct['start_time']} | {ct['category']} - {ct['desc']} | ... | ... |\n")

            # ── Journal entries for this day ──────────────────────────────
            # Past days: read from stored snapshot; active day: read live state.
            if idx == self.active_day_idx:
                src = {
                    "morning":   self.journal_morning,
                    "afternoon": self.journal_afternoon,
                }
            else:
                src = day.get("journals", {"morning": None, "afternoon": None})

            for jkey, jlabel in (("morning",   "MORNING JOURNAL"),
                                  ("afternoon", "AFTERNOON JOURNAL")):
                j = src.get(jkey) if src else None
                if j and j.get("locked"):
                    ts_str = fmt_ts(j["timestamp"]) if j.get("timestamp") else "?"
                    lines.append(f"\n◈ {jlabel} — {ts_str}\n")
                    lines.append(j["text"] + "\n")
                elif idx < self.active_day_idx:
                    # Past day with no locked journal entry
                    lines.append(f"\n◈ {jlabel} — NOT THIS ONE, BUD :P\n")

        content = "".join(lines)
        self.txt_output.config(state="normal")
        self.txt_output.delete("1.0", "end")
        self.txt_output.insert("1.0", content)
        self.txt_output.config(state="disabled")

    def _get_log_text(self) -> str:
        return self.txt_output.get("1.0", "end-1c")

    # ── HASH & FRONTMATTER ────────────────────────────────────────────────────
    def _compute_hash(self, name: str, org: str, export_ts: str) -> str:
        seed = f"{name}{org}{fmt_ts(self.open_ts)}{export_ts}"
        return hashlib.sha256(seed.encode()).hexdigest()[:16]

    def _build_frontmatter(self, export_ts: str, hash_val: str) -> str:
        name = self.var_name.get().strip() or "Unknown"
        org  = self.var_org.get().strip()  or "Unknown"
        return "\n".join([
            "---",
            f'app_opened:      "{fmt_ts(self.open_ts)}"',
            f'exported_at:     "{export_ts}"',
            f'operator:        "{name}"',
            f'org:             "{org}"',
            f'validation_hash: "{hash_val}"',
            "---",
            "",
        ])

    # ── HASHBROWNS FILE ───────────────────────────────────────────────────────
    def _init_hashbrowns_file(self, path: str, auditor: str, auditor_org: str,
                               created_ts: str, key_half_a: str, file_hmac: str):
        """Write the header block of a new hashbrowns.yaml."""
        lines = [
            "rtf_hashbrowns:\n",
            f'  created:     "{created_ts}"\n',
            f'  auditor:     "{auditor}"\n',
            f'  auditor_org: "{auditor_org}"\n',
        ]
        if key_half_a:
            lines.append(f'  key_half_a:  "{key_half_a}"\n')
            lines.append(f'  file_hmac:   "{file_hmac}"\n')
        lines.append("entries:\n")
        with open(path, "w", encoding="utf-8") as f:
            f.writelines(lines)

    def _append_hashbrowns_entry(self, path: str, name: str,
                                  org: str, export_ts: str, h: str):
        entry = (
            f'  - operator: "{name}"\n'
            f'    org:      "{org}"\n'
            f'    created:  "{export_ts}"\n'
            f'    hash:     "{h}"\n'
        )
        with open(path, "a", encoding="utf-8") as f:
            f.write(entry)

    def _handle_hashbrowns(self, name: str, org: str, export_ts: str) -> str:
        """Manage hashbrowns.yaml. Returns hash string or 'skipped'."""
        hb_path     = os.path.join(script_dir(), "hashbrowns.yaml")
        file_exists = os.path.isfile(hb_path)

        if self.hashbrowns_consent is False:
            return "skipped"

        # ── File absent and not yet asked ──────────────────────────────────
        if not file_exists and self.hashbrowns_consent is None:
            answer = messagebox.askyesno(
                "Hashbrowns // Audit Trail",
                "No hashbrowns.yaml found next to this script.\n\n"
                "Create one? It keeps a sequential audit trail:\n"
                "  operator · org · timestamp · validation hash\n\n"
                "Choosing No skips hashing for this entire session.",
                parent=self
            )
            self.hashbrowns_consent = answer
            if not answer:
                return "skipped"

            # ── Audit setup ────────────────────────────────────────────────
            setup = HashbrownsSetupDialog(self)
            self.wait_window(setup)

            auditor     = setup.result_auditor
            auditor_org = setup.result_org
            created_ts  = fmt_ts(datetime.now())
            key_half_a  = ""
            file_hmac   = ""

            if auditor or auditor_org:
                full_key   = secrets.token_hex(32)   # 64 hex chars
                key_half_a = full_key[:32]
                key_half_b = full_key[32:]
                file_hmac  = compute_file_hmac(
                    full_key, auditor, auditor_org, created_ts)
                # Show Key B — modal, requires explicit acknowledgment
                kd = KeyDisplayDialog(self, key_half_b)
                self.wait_window(kd)

            self._init_hashbrowns_file(
                hb_path, auditor, auditor_org, created_ts, key_half_a, file_hmac)

        # ── Compute entry hash and append ──────────────────────────────────
        h = self._compute_hash(name, org, export_ts)
        try:
            self._append_hashbrowns_entry(hb_path, name, org, export_ts, h)
        except OSError as exc:
            messagebox.showwarning("Hashbrowns Error",
                                   f"Could not write to hashbrowns.yaml:\n{exc}",
                                   parent=self)
        return h

    def _build_full_md(self) -> str:
        """YAML frontmatter + work log + all days' journal entries."""
        name      = self.var_name.get().strip() or "Unknown"
        org       = self.var_org.get().strip()  or "Unknown"
        export_ts = fmt_ts(datetime.now())

        # Snapshot live journals into the active day before exporting
        self._save_journals_to_day()

        hash_val = self._handle_hashbrowns(name, org, export_ts)
        fm       = self._build_frontmatter(export_ts, hash_val)
        body     = self._get_log_text().strip()

        # Collect locked journal entries from every day
        journal_lines = []
        for day in self.days:
            for jkey, jlabel in (("morning",   "Morning Journal"),
                                  ("afternoon", "Afternoon Journal")):
                j = (day.get("journals") or {}).get(jkey)
                if j and j.get("locked"):
                    ts_str = fmt_ts(j["timestamp"]) if j.get("timestamp") else "?"
                    journal_lines.append(f"\n## {day['date']} — {jlabel}\n")
                    journal_lines.append(f"*Completed: {ts_str}*\n\n")
                    journal_lines.append(j["text"] + "\n")

        if journal_lines:
            body += "\n\n---\n" + "".join(journal_lines)

        return fm + "\n" + body

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
        # Snapshot the current journals into the outgoing day before clearing
        self._save_journals_to_day()
        self.days.append({
            "key":      today_key(),
            "date":     fmt_date(datetime.now()),
            "lines":    [],
            "journals": {"morning": None, "afternoon": None},
        })
        self.active_day_idx = len(self.days) - 1
        self.current_task   = None
        self._set_status(False)
        self._refresh_log()
        self._reset_journals()

    def _save_journals_to_day(self):
        """Copy live journal state into the active day's dict."""
        day = self._active_day()
        if "journals" not in day:
            day["journals"] = {"morning": None, "afternoon": None}
        for key in ("morning", "afternoon"):
            state = getattr(self, f"journal_{key}")
            day["journals"][key] = dict(state)   # shallow copy is enough

    def _reset_journals(self):
        for key in ("morning", "afternoon"):
            state = getattr(self, f"journal_{key}")
            state["text"]      = ""
            state["timestamp"] = None
            state["locked"]    = False
            txt = getattr(self, f"_jnl_{key}_txt")
            ts  = getattr(self, f"_jnl_{key}_ts")
            btn = getattr(self, f"_jnl_{key}_btn")
            clr = getattr(self, f"_jnl_{key}_clr")
            txt.config(state="normal", highlightbackground=clr,
                       fg=TEXT_MAIN, insertbackground=clr)
            txt.delete("1.0", "end")
            ts.config(text="")
            btn.config(text="[ COMPLETE ]", fg=clr,
                       highlightbackground=clr, cursor="hand2")

    def _on_copy(self):
        text = self._build_full_md()
        self.clipboard_clear()
        self.clipboard_append(text)
        messagebox.showinfo("Copied", "Worklog (with YAML frontmatter) copied to clipboard.")

    def _on_export(self):
        text = self._build_full_md().strip()
        if not text:
            messagebox.showwarning("Empty", "Nothing to export yet.")
            return
        name         = (self.var_name.get().strip() or "worklog").replace(" ", "_")
        default_name = f"worklog_{name}_{today_key()}.md"
        path = filedialog.asksaveasfilename(
            defaultextension=".md",
            filetypes=[("Markdown files", "*.md"),
                       ("Text files",     "*.txt"),
                       ("All files",      "*.*")],
            initialfile=default_name,
            title="Download Worklog"
        )
        if path:
            with open(path, "w", encoding="utf-8") as f:
                f.write(text)
            self.exported = True
            messagebox.showinfo("Exported", f"Saved to:\n{path}")

    def _on_close(self):
        """WM_DELETE_WINDOW handler — warn if there's unsaved log content."""
        has_content = any(day["lines"] for day in self.days)
        if has_content and not self.exported:
            answer = messagebox.askyesno(
                "Close without downloading?",
                "You have logged tasks that haven't been downloaded.\n\n"
                "All data will be lost when the app closes.\n\n"
                "Close anyway?",
                icon="warning",
                parent=self
            )
            if not answer:
                return
        self.destroy()


# ─── BASE DIALOG ──────────────────────────────────────────────────────────────
class BaseDialog(tk.Toplevel):
    def __init__(self, app: WorkdayLogger, title: str, border_color: str = NEON_PINK):
        super().__init__(app)
        self.app = app
        # Associate with parent so the dialog stays in front and isn't a
        # separate taskbar entry; only when the parent is actually visible.
        if app.winfo_viewable():
            self.transient(app)
        self.title(title)
        self.configure(bg=BG_PANEL)
        self.resizable(False, False)
        self.grab_set()
        self.config(highlightbackground=border_color, highlightthickness=3)
        self.bind("<Escape>", lambda e: self.destroy())
        self._center()

    def _center(self):
        self.update_idletasks()
        w, h = self.winfo_reqwidth(), self.winfo_reqheight()
        x = self.app.winfo_x() + (self.app.winfo_width()  - w) // 2
        y = self.app.winfo_y() + (self.app.winfo_height() - h) // 2
        self.geometry(f"+{x}+{y}")


# ─── HASHBROWNS SETUP DIALOG ──────────────────────────────────────────────────
class HashbrownsSetupDialog(BaseDialog):
    """Collect optional auditor info when creating a new hashbrowns.yaml."""

    def __init__(self, app: WorkdayLogger):
        self.result_auditor = ""
        self.result_org     = ""
        super().__init__(app, "> HASHBROWNS // AUDIT SETUP <", border_color=NEON_PURP)
        self.minsize(460, 310)
        self.protocol("WM_DELETE_WINDOW", self._skip)

        frame = tk.Frame(self, bg=BG_PANEL, padx=22, pady=18)
        frame.pack(fill="both", expand=True)
        frame.columnconfigure(1, weight=1)

        tk.Label(frame, text="> HASHBROWNS // AUDIT SETUP <",
                 font=("Courier", 13, "bold"), fg=NEON_PURP, bg=BG_PANEL)\
            .grid(row=0, column=0, columnspan=2, pady=(0, 8))

        tk.Label(frame,
                 text="Optionally assign an auditor to this trail.\n"
                      "If either field is filled, a split verification\n"
                      "key will be generated for independent audit.\n"
                      "Leave both blank to create the file without a key.",
                 font=FONT_MONO_SM, fg=TEXT_DIM, bg=BG_PANEL, justify="left")\
            .grid(row=1, column=0, columnspan=2, sticky="w", pady=(0, 14))

        for row, (label, attr) in enumerate(
            (("AUDITOR NAME:", "var_auditor"), ("AUDITOR ORG:", "var_aud_org")),
            start=2
        ):
            tk.Label(frame, text=label, font=FONT_MONO_SM, fg=NEON_PURP,
                     bg=BG_PANEL, anchor="w", width=16)\
                .grid(row=row, column=0, sticky="w", pady=5)
            var = tk.StringVar()
            setattr(self, attr, var)
            tk.Entry(frame, textvariable=var, font=FONT_MONO,
                     bg=BG_ELEV, fg="white", insertbackground="white",
                     relief="flat", highlightbackground=NEON_PURP,
                     highlightthickness=1)\
                .grid(row=row, column=1, sticky="ew", pady=5)

        tk.Frame(frame, bg=NEON_PURP, height=1)\
            .grid(row=4, column=0, columnspan=2, sticky="ew", pady=12)

        btn_row = tk.Frame(frame, bg=BG_PANEL)
        btn_row.grid(row=5, column=0, columnspan=2, sticky="ew")
        btn_row.columnconfigure(0, weight=1)
        btn_row.columnconfigure(1, weight=1)

        tk.Button(btn_row, text="> CONFIRM <", command=self._confirm,
                  font=("Courier", 12, "bold"), fg=NEON_PURP, bg=BG_PANEL,
                  relief="flat", highlightbackground=NEON_PURP, highlightthickness=2,
                  pady=6, cursor="hand2")\
            .grid(row=0, column=0, padx=(0, 4), sticky="ew")
        tk.Button(btn_row, text="> SKIP <", command=self._skip,
                  font=("Courier", 12, "bold"), fg=TEXT_DIM, bg=BG_PANEL,
                  relief="flat", highlightbackground=TEXT_DIM, highlightthickness=2,
                  pady=6, cursor="hand2")\
            .grid(row=0, column=1, padx=(4, 0), sticky="ew")

        self.bind("<Return>", lambda e: self._confirm())
        self._center()

    def _confirm(self):
        self.result_auditor = self.var_auditor.get().strip()
        self.result_org     = self.var_aud_org.get().strip()
        self.destroy()

    def _skip(self):
        self.result_auditor = ""
        self.result_org     = ""
        self.destroy()


# ─── KEY DISPLAY DIALOG ───────────────────────────────────────────────────────
class KeyDisplayDialog(tk.Toplevel):
    """
    Shows Key Half B. Cannot be dismissed with Escape or the window manager —
    requires the explicit acknowledgment button.

    Follows the tkinter.simpledialog pattern:
        withdraw → build → deiconify → wait_visibility → grab_set
    so the window is fully mapped before the grab is set.
    """

    def __init__(self, app: WorkdayLogger, key_half_b: str):
        super().__init__(app)
        self.app = app

        # ── Hide immediately while we build, then show in one clean pass ──
        self.withdraw()
        if app.winfo_viewable():
            self.transient(app)

        self.title("> AUDITOR KEY B — STORE THIS NOW <")
        self.configure(bg=BG_PANEL)
        self.resizable(False, False)
        self.config(highlightbackground=NEON_YELL, highlightthickness=3)
        self.protocol("WM_DELETE_WINDOW", lambda: None)   # no X-close
        self.bind("<Escape>", lambda e: None)              # no Escape
        self.minsize(520, 350)

        frame = tk.Frame(self, bg=BG_PANEL, padx=22, pady=18)
        frame.pack(fill="both", expand=True)

        tk.Label(frame, text="⚠  AUDITOR KEY B  ⚠",
                 font=("Courier", 15, "bold"), fg=NEON_YELL, bg=BG_PANEL)\
            .pack(pady=(0, 8))

        tk.Label(frame,
                 text="This key will NEVER be shown again.\n"
                      "Copy it and store it separately from hashbrowns.yaml.\n"
                      "Both halves are required to validate the audit trail.",
                 font=FONT_MONO_SM, fg=TEXT_DIM, bg=BG_PANEL, justify="center")\
            .pack(pady=(0, 12))

        # Selectable key box
        key_box = tk.Frame(frame, bg=BG_ELEV,
                           highlightbackground=NEON_YELL, highlightthickness=2)
        key_box.pack(fill="x", pady=(0, 8))

        key_txt = tk.Text(key_box, font=("Courier", 14, "bold"),
                          bg=BG_ELEV, fg=NEON_YELL,
                          height=1, relief="flat", padx=12, pady=12,
                          wrap="none", cursor="xterm")
        key_txt.insert("1.0", key_half_b)
        key_txt.pack(fill="x")

        def copy_key():
            app.clipboard_clear()
            app.clipboard_append(key_half_b)
            copy_btn.config(text="[ COPIED ✓ ]", fg=NEON_LIME,
                            highlightbackground=NEON_LIME)

        copy_btn = tk.Button(frame, text="[ COPY KEY B ]",
                             command=copy_key, font=FONT_MONO_SM,
                             fg=NEON_YELL, bg=BG_PANEL, relief="flat",
                             highlightbackground=NEON_YELL, highlightthickness=1,
                             padx=8, pady=4, cursor="hand2")
        copy_btn.pack(pady=(0, 12))

        tk.Frame(frame, bg=NEON_YELL, height=1).pack(fill="x", pady=(0, 12))

        tk.Button(frame, text="> I HAVE STORED KEY B — CONTINUE <",
                  command=self.destroy,
                  font=("Courier", 11, "bold"), fg=NEON_LIME, bg=BG_PANEL,
                  relief="flat", highlightbackground=NEON_LIME, highlightthickness=2,
                  pady=8, cursor="hand2")\
            .pack(fill="x")

        # Position window, then reveal and grab in the correct order.
        # grab_set() must come AFTER wait_visibility() or the grab may be set
        # before the window manager has mapped the window, leaving a blank shell.
        self._center()
        self.deiconify()        # reveal now that content is fully built
        self.focus_set()
        self.wait_visibility()  # block until WM confirms window is on screen
        self.grab_set()         # only now is it safe to capture all input

    def _center(self):
        self.update_idletasks()
        w, h = self.winfo_reqwidth(), self.winfo_reqheight()
        x = self.app.winfo_x() + (self.app.winfo_width()  - w) // 2
        y = self.app.winfo_y() + (self.app.winfo_height() - h) // 2
        self.geometry(f"+{x}+{y}")


# ─── TASK DIALOGS ─────────────────────────────────────────────────────────────
class StartTaskDialog(BaseDialog):
    def __init__(self, app: WorkdayLogger):
        super().__init__(app, "> START NEW TASK <")
        self.minsize(380, 260)

        frame = tk.Frame(self, bg=BG_PANEL, padx=20, pady=16)
        frame.pack(fill="both", expand=True)

        tk.Label(frame, text="> START NEW TASK <", font=("Courier", 14, "bold"),
                 fg=NEON_PINK, bg=BG_PANEL).pack(pady=(0, 12))

        tk.Label(frame, text="CATEGORY:", font=FONT_MONO_SM,
                 fg=NEON_CYAN, bg=BG_PANEL, anchor="w").pack(fill="x")
        self.var_cat = tk.StringVar()
        cats   = app._all_cats()
        cat_cb = ttk.Combobox(frame, textvariable=self.var_cat, values=cats,
                              font=FONT_MONO, state="readonly", width=40)
        cat_cb.pack(fill="x", pady=(2, 10))
        self._style_combo(cat_cb)

        tk.Label(frame, text="TASK DESCRIPTION:", font=FONT_MONO_SM,
                 fg=NEON_CYAN, bg=BG_PANEL, anchor="w").pack(fill="x")
        self.var_desc = tk.StringVar()
        tk.Entry(frame, textvariable=self.var_desc, font=FONT_MONO,
                 bg=BG_ELEV, fg="white", insertbackground="white",
                 relief="flat", highlightbackground=NEON_CYAN,
                 highlightthickness=1).pack(fill="x", pady=(2, 14))

        btn_row = tk.Frame(frame, bg=BG_PANEL)
        btn_row.pack(fill="x")
        btn_row.columnconfigure(0, weight=1)
        btn_row.columnconfigure(1, weight=1)

        tk.Button(btn_row, text="> COMMIT <", command=self._commit,
                  font=("Courier", 12, "bold"), fg=NEON_CYAN, bg=BG_PANEL,
                  relief="flat", highlightbackground=NEON_CYAN, highlightthickness=2,
                  pady=6, cursor="hand2").grid(row=0, column=0, padx=(0, 4), sticky="ew")
        tk.Button(btn_row, text="> CANCEL <", command=self.destroy,
                  font=("Courier", 12, "bold"), fg=TEXT_DIM, bg=BG_PANEL,
                  relief="flat", highlightbackground=TEXT_DIM, highlightthickness=2,
                  pady=6, cursor="hand2").grid(row=0, column=1, padx=(4, 0), sticky="ew")

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
        if not cat:
            messagebox.showwarning("Missing", "Please select a category.", parent=self)
            return
        if not desc:
            messagebox.showwarning("Missing", "Please enter a task description.", parent=self)
            return

        now = datetime.now()
        day = self.app._active_day()

        if self.app.current_task:
            ct  = self.app.current_task
            hrs = calc_hours(ct["start_dt"], now)
            day["lines"].append({
                "start": ct["start_time"],
                "desc":  f"{ct['category']} - {ct['desc']} (switched at {fmt_time(now)})",
                "end":   fmt_time(now),
                "hours": hrs,
            })

        self.app.current_task = {
            "start_dt":   now,
            "start_time": fmt_time(now),
            "category":   cat,
            "desc":       desc,
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
            tk.Label(row, text=f"{label}:", font=FONT_MONO_SM, fg=NEON_CYAN,
                     bg=BG_PANEL, width=14, anchor="w").pack(side="left")
            tk.Label(row, text=value, font=FONT_MONO, fg=color,
                     bg=BG_PANEL, anchor="w").pack(side="left")

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
                  pady=6, cursor="hand2").grid(row=0, column=0, padx=(0, 4), sticky="ew")
        tk.Button(btn_row, text="> CANCEL <", command=self.destroy,
                  font=("Courier", 12, "bold"), fg=TEXT_DIM, bg=BG_PANEL,
                  relief="flat", highlightbackground=TEXT_DIM, highlightthickness=2,
                  pady=6, cursor="hand2").grid(row=0, column=1, padx=(4, 0), sticky="ew")

        self._now   = now
        self._hours = hrs
        self._center()

    def _commit(self):
        ct = self.app.current_task
        self.app._active_day()["lines"].append({
            "start": ct["start_time"],
            "desc":  f"{ct['category']} - {ct['desc']}",
            "end":   fmt_time(self._now),
            "hours": self._hours,
        })
        self.app.current_task = None
        self.app._set_status(False)
        self.app._refresh_log()
        self.destroy()


# ─── CATEGORIES DIALOG ────────────────────────────────────────────────────────
class CategoriesDialog(BaseDialog):
    def __init__(self, app: WorkdayLogger):
        super().__init__(app, "> CATEGORIES <", border_color=NEON_ORNG)
        self.minsize(360, 420)

        frame = tk.Frame(self, bg=BG_PANEL, padx=16, pady=14)
        frame.pack(fill="both", expand=True)
        frame.rowconfigure(2, weight=1)
        frame.columnconfigure(0, weight=1)

        tk.Label(frame, text="> MANAGE CATEGORIES <", font=("Courier", 13, "bold"),
                 fg=NEON_ORNG, bg=BG_PANEL)\
            .grid(row=0, column=0, columnspan=2, pady=(0, 10))

        add_frame = tk.Frame(frame, bg=BG_PANEL)
        add_frame.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(0, 8))
        add_frame.columnconfigure(0, weight=1)

        self.var_new = tk.StringVar()
        tk.Entry(add_frame, textvariable=self.var_new, font=FONT_MONO,
                 bg=BG_ELEV, fg="white", insertbackground="white",
                 relief="flat", highlightbackground=NEON_ORNG,
                 highlightthickness=1, width=24)\
            .grid(row=0, column=0, sticky="ew", padx=(0, 6))
        tk.Button(add_frame, text="+ ADD", command=self._add,
                  font=FONT_MONO_SM, fg=NEON_ORNG, bg=BG_PANEL,
                  relief="flat", highlightbackground=NEON_ORNG, highlightthickness=1,
                  padx=8, pady=4, cursor="hand2").grid(row=0, column=1)

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
                  pady=4, cursor="hand2")\
            .grid(row=3, column=0, columnspan=2, sticky="ew", pady=(0, 6))

        tk.Label(frame, text="⚠ Custom categories are session-only",
                 font=FONT_MONO_SM, fg=TEXT_DIM, bg=BG_PANEL)\
            .grid(row=4, column=0, columnspan=2)

        tk.Button(frame, text="> CLOSE <", command=self.destroy,
                  font=("Courier", 12, "bold"), fg=TEXT_DIM, bg=BG_PANEL,
                  relief="flat", highlightbackground=TEXT_DIM, highlightthickness=2,
                  pady=6, cursor="hand2")\
            .grid(row=5, column=0, columnspan=2, sticky="ew", pady=(8, 0))

        self.var_new.trace_add("write", lambda *_: None)
        self.bind("<Return>", lambda e: self._add())
        self._center()

    def _populate_list(self):
        self.listbox.delete(0, "end")
        for c in DEFAULT_CATS:
            self.listbox.insert("end", f"  {c}  [built-in]")
        for c in self.app.custom_cats:
            self.listbox.insert("end", f"  {c}  [custom]")
            self.listbox.itemconfig(self.listbox.size() - 1, fg=NEON_ORNG)

    def _add(self):
        val = self.var_new.get().strip().replace(" ", "-")
        if not val or val in DEFAULT_CATS + self.app.custom_cats:
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
        if idx < len(DEFAULT_CATS):
            messagebox.showinfo("Built-in",
                                "Built-in categories cannot be deleted.", parent=self)
            return
        del self.app.custom_cats[idx - len(DEFAULT_CATS)]
        self._populate_list()


# ─── ENTRY POINT ─────────────────────────────────────────────────────────────
if __name__ == "__main__":
    app = WorkdayLogger()
    app.mainloop()
