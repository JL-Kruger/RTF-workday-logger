#!/usr/bin/env python3
"""
RTF-AUDIT // HASHBROWNS VALIDATOR
Validates a hashbrowns.yaml audit trail produced by RTF-workday-logger.
Stdlib only (tkinter, hmac, hashlib). No dependencies.
Run with: python RTF-audit.py
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import hashlib
import hmac as _hmac
import os
import sys


# ─── COLOUR PALETTE (matches logger) ─────────────────────────────────────────
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


# ─── PARSER ───────────────────────────────────────────────────────────────────
def parse_hashbrowns(path: str) -> tuple[dict, list[dict]]:
    """
    Parse hashbrowns.yaml into (header_dict, entries_list).

    Expected format:
        rtf_hashbrowns:
          created:     "..."
          auditor:     "..."
          auditor_org: "..."
          key_half_a:  "..."   # optional
          file_hmac:   "..."   # optional
        entries:
          - operator: "..."
            org:      "..."
            created:  "..."
            hash:     "..."
    """
    header: dict        = {}
    entries: list[dict] = []
    current_entry       = None
    section             = None   # 'header' | 'entries'

    with open(path, "r", encoding="utf-8") as f:
        for raw_line in f:
            line    = raw_line.rstrip("\n")
            stripped = line.strip()

            if not stripped:
                continue

            if line.startswith("rtf_hashbrowns:"):
                section = "header"
                continue

            if line.startswith("entries:"):
                if current_entry is not None:
                    entries.append(current_entry)
                    current_entry = None
                section = "entries"
                continue

            if section == "header":
                if ": " in stripped:
                    k, _, v = stripped.partition(": ")
                    header[k.strip()] = v.strip().strip('"')

            elif section == "entries":
                if stripped.startswith("- "):
                    if current_entry is not None:
                        entries.append(current_entry)
                    current_entry = {}
                    rest = stripped[2:]
                    if ": " in rest:
                        k, _, v = rest.partition(": ")
                        current_entry[k.strip()] = v.strip().strip('"')
                elif stripped and ": " in stripped and current_entry is not None:
                    k, _, v = stripped.partition(": ")
                    current_entry[k.strip()] = v.strip().strip('"')

    if current_entry is not None:
        entries.append(current_entry)

    return header, entries


def verify_file_hmac(full_key: str, auditor: str,
                     auditor_org: str, created: str, stored: str) -> bool:
    msg      = f"{auditor}{auditor_org}{created}".encode()
    computed = _hmac.new(full_key.encode(), msg, hashlib.sha256).hexdigest()[:32]
    return _hmac.compare_digest(computed, stored)


# ─── KEY B DIALOG ─────────────────────────────────────────────────────────────
class KeyBDialog(tk.Toplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.withdraw()                          # hide while building
        if parent.winfo_viewable():
            self.transient(parent)
        self.title("> ENTER AUDITOR KEY B <")
        self.configure(bg=BG_PANEL)
        self.resizable(False, False)
        self.config(highlightbackground=NEON_YELL, highlightthickness=3)
        self.result = ""
        self.minsize(460, 210)

        frame = tk.Frame(self, bg=BG_PANEL, padx=22, pady=18)
        frame.pack(fill="both", expand=True)

        tk.Label(frame, text="> ENTER AUDITOR KEY B <",
                 font=("Courier", 13, "bold"), fg=NEON_YELL, bg=BG_PANEL)\
            .pack(pady=(0, 8))
        tk.Label(frame,
                 text="Enter the auditor's key half (Key B)\n"
                      "to verify this file's HMAC signature.",
                 font=FONT_MONO_SM, fg=TEXT_DIM, bg=BG_PANEL, justify="center")\
            .pack(pady=(0, 10))

        self.var_key = tk.StringVar()
        tk.Entry(frame, textvariable=self.var_key,
                 font=("Courier", 13),
                 bg=BG_ELEV, fg=NEON_YELL, insertbackground=NEON_YELL,
                 relief="flat", highlightbackground=NEON_YELL,
                 highlightthickness=1)\
            .pack(fill="x", pady=(0, 14))

        btn_row = tk.Frame(frame, bg=BG_PANEL)
        btn_row.pack(fill="x")
        btn_row.columnconfigure(0, weight=1)
        btn_row.columnconfigure(1, weight=1)

        tk.Button(btn_row, text="> VERIFY <", command=self._verify,
                  font=("Courier", 12, "bold"), fg=NEON_YELL, bg=BG_PANEL,
                  relief="flat", highlightbackground=NEON_YELL, highlightthickness=2,
                  pady=6, cursor="hand2")\
            .grid(row=0, column=0, padx=(0, 4), sticky="ew")
        tk.Button(btn_row, text="> SKIP <", command=self.destroy,
                  font=("Courier", 12, "bold"), fg=TEXT_DIM, bg=BG_PANEL,
                  relief="flat", highlightbackground=TEXT_DIM, highlightthickness=2,
                  pady=6, cursor="hand2")\
            .grid(row=0, column=1, padx=(4, 0), sticky="ew")

        self.bind("<Return>", lambda e: self._verify())
        self.bind("<Escape>", lambda e: self.destroy())
        self._center(parent)
        self.deiconify()        # reveal now content is fully built
        self.focus_set()
        self.wait_visibility()  # wait for WM to map the window
        self.grab_set()         # only now safe to grab

    def _center(self, parent):
        self.update_idletasks()
        w, h = self.winfo_reqwidth(), self.winfo_reqheight()
        x = parent.winfo_x() + (parent.winfo_width()  - w) // 2
        y = parent.winfo_y() + (parent.winfo_height() - h) // 2
        self.geometry(f"+{x}+{y}")

    def _verify(self):
        self.result = self.var_key.get().strip()
        self.destroy()


# ─── MAIN AUDIT APP ───────────────────────────────────────────────────────────
class RTFAudit(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("RTF-AUDIT // HASHBROWNS VALIDATOR")
        self.configure(bg=BG_DARK)
        self.minsize(760, 580)

        self.hb_path  = None
        self.header: dict        = {}
        self.entries: list[dict] = []

        self._build_ui()

        # Auto-load if a hashbrowns.yaml sits next to this script
        auto_path = os.path.join(
            os.path.dirname(os.path.abspath(sys.argv[0])), "hashbrowns.yaml")
        if os.path.isfile(auto_path):
            self._load_from_path(auto_path)

    # ── UI ────────────────────────────────────────────────────────────────────
    def _build_ui(self):
        self.rowconfigure(0, weight=1)
        self.columnconfigure(0, weight=1)

        root = tk.Frame(self, bg=BG_DARK, padx=16, pady=16)
        root.grid(row=0, column=0, sticky="nsew")
        root.columnconfigure(0, weight=1)
        root.rowconfigure(3, weight=1)

        # Header
        hdr = tk.Frame(root, bg=BG_PANEL, padx=12, pady=10,
                       highlightbackground=NEON_PURP, highlightthickness=2)
        hdr.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        tk.Label(hdr, text="RTF-AUDIT", font=("Courier", 22, "bold"),
                 fg=NEON_PURP, bg=BG_PANEL).pack()
        tk.Label(hdr, text="HASHBROWNS TRAIL VALIDATOR // REMEMBER TO FORGET",
                 font=FONT_MONO_SM, fg=NEON_CYAN, bg=BG_PANEL).pack()

        # Load bar
        load_frame = tk.Frame(root, bg=BG_DARK)
        load_frame.grid(row=1, column=0, sticky="ew", pady=(0, 8))
        load_frame.columnconfigure(1, weight=1)

        tk.Button(load_frame, text="> LOAD HASHBROWNS.YAML <",
                  command=self._pick_file,
                  font=("Courier", 12, "bold"), fg=NEON_PURP, bg=BG_PANEL,
                  relief="flat", highlightbackground=NEON_PURP, highlightthickness=2,
                  padx=10, pady=8, cursor="hand2")\
            .grid(row=0, column=0, padx=(0, 10))

        self.lbl_path = tk.Label(load_frame, text="No file loaded",
                                  font=FONT_MONO_SM, fg=TEXT_DIM, bg=BG_DARK)
        self.lbl_path.grid(row=0, column=1, sticky="w")

        # Info panel
        info_outer = tk.Frame(root, bg=BG_PANEL,
                               highlightbackground=NEON_PURP, highlightthickness=1)
        info_outer.grid(row=2, column=0, sticky="ew", pady=(0, 8))
        info_outer.columnconfigure(1, weight=1)

        self._info = {}
        rows = [
            ("created",     "CREATED",     NEON_CYAN),
            ("auditor",     "AUDITOR",     NEON_PURP),
            ("auditor_org", "AUDITOR ORG", NEON_PURP),
            ("key_status",  "KEY STATUS",  NEON_YELL),
            ("hmac_status", "FILE HMAC",   NEON_YELL),
        ]
        for i, (key, label, color) in enumerate(rows):
            tk.Label(info_outer, text=f"  {label}:", font=FONT_MONO_SM,
                     fg=color, bg=BG_PANEL, width=16, anchor="w")\
                .grid(row=i, column=0, sticky="w", padx=(8, 4), pady=3)
            lbl = tk.Label(info_outer, text="—", font=FONT_MONO_SM,
                           fg=TEXT_DIM, bg=BG_PANEL, anchor="w")
            lbl.grid(row=i, column=1, sticky="w", pady=3, padx=(0, 8))
            self._info[key] = lbl

        # Entries area
        entries_frame = tk.Frame(root, bg=BG_PANEL,
                                  highlightbackground=NEON_CYAN, highlightthickness=2)
        entries_frame.grid(row=3, column=0, sticky="nsew")
        entries_frame.columnconfigure(0, weight=1)
        entries_frame.rowconfigure(1, weight=1)

        entries_hdr = tk.Frame(entries_frame, bg=BG_PANEL)
        entries_hdr.grid(row=0, column=0, sticky="ew", padx=8, pady=(6, 2))
        tk.Label(entries_hdr, text="// AUDIT ENTRIES", font=FONT_BIG,
                 fg=NEON_CYAN, bg=BG_PANEL).pack(side="left")
        self.lbl_count = tk.Label(entries_hdr, text="", font=FONT_MONO_SM,
                                   fg=TEXT_DIM, bg=BG_PANEL)
        self.lbl_count.pack(side="right")

        self.txt = tk.Text(entries_frame, font=FONT_MONO,
                           bg=BG_ELEV, fg=TEXT_MAIN,
                           relief="flat", padx=10, pady=10,
                           state="disabled", wrap="none",
                           highlightthickness=0)
        self.txt.grid(row=1, column=0, sticky="nsew", padx=2, pady=2)

        sy = tk.Scrollbar(entries_frame, command=self.txt.yview,
                           bg=BG_DARK, troughcolor=BG_ELEV)
        sy.grid(row=1, column=1, sticky="ns")
        sx = tk.Scrollbar(entries_frame, orient="horizontal",
                           command=self.txt.xview,
                           bg=BG_DARK, troughcolor=BG_ELEV)
        sx.grid(row=2, column=0, sticky="ew")
        self.txt.configure(yscrollcommand=sy.set, xscrollcommand=sx.set)

        # Text colour tags
        self.txt.tag_config("ok",  foreground=NEON_LIME)
        self.txt.tag_config("err", foreground=NEON_RED)
        self.txt.tag_config("dim", foreground=TEXT_DIM)
        self.txt.tag_config("hdr", foreground=NEON_CYAN)
        self.txt.tag_config("key", foreground=NEON_YELL)

    # ── FILE LOADING ──────────────────────────────────────────────────────────
    def _pick_file(self):
        path = filedialog.askopenfilename(
            title="Select hashbrowns.yaml",
            filetypes=[("YAML files", "*.yaml"), ("All files", "*.*")],
            initialfile="hashbrowns.yaml"
        )
        if path:
            self._load_from_path(path)

    def _load_from_path(self, path: str):
        try:
            header, entries = parse_hashbrowns(path)
        except Exception as exc:
            messagebox.showerror("Parse Error",
                                 f"Could not parse file:\n{exc}", parent=self)
            return

        self.hb_path = path
        self.header  = header
        self.entries = entries
        self.lbl_path.config(text=os.path.basename(path), fg=NEON_LIME)

        # Populate info panel
        self._info["created"].config(
            text=header.get("created", "—") or "—", fg=TEXT_MAIN)
        self._info["auditor"].config(
            text=header.get("auditor",     "—") or "—", fg=TEXT_MAIN)
        self._info["auditor_org"].config(
            text=header.get("auditor_org", "—") or "—", fg=TEXT_MAIN)

        has_key = bool(header.get("key_half_a", "").strip())

        if has_key:
            self._info["key_status"].config(
                text="Split key present  —  enter Key B to verify", fg=NEON_YELL)
            self._info["hmac_status"].config(text="Pending Key B …", fg=TEXT_DIM)
            self._prompt_key_b()
        else:
            self._info["key_status"].config(
                text="No split key (file created without auditor)", fg=TEXT_DIM)
            self._info["hmac_status"].config(text="N/A", fg=TEXT_DIM)
            self._display_entries(verified=None)

    # ── KEY B & VERIFICATION ──────────────────────────────────────────────────
    def _prompt_key_b(self):
        dlg = KeyBDialog(self)
        self.wait_window(dlg)

        if not dlg.result:
            self._info["hmac_status"].config(text="Skipped by user", fg=TEXT_DIM)
            self._display_entries(verified=None)
            return

        key_half_a  = self.header.get("key_half_a",  "")
        stored_hmac = self.header.get("file_hmac",   "")
        auditor     = self.header.get("auditor",     "")
        auditor_org = self.header.get("auditor_org", "")
        created     = self.header.get("created",     "")
        full_key    = key_half_a + dlg.result

        ok = verify_file_hmac(full_key, auditor, auditor_org, created, stored_hmac)

        if ok:
            self._info["hmac_status"].config(
                text="✓  VERIFIED — file is authentic", fg=NEON_LIME)
        else:
            self._info["hmac_status"].config(
                text="✗  FAILED — key incorrect or file tampered", fg=NEON_RED)

        self._display_entries(verified=ok)

    # ── ENTRY DISPLAY ─────────────────────────────────────────────────────────
    def _display_entries(self, verified: bool | None):
        self.txt.config(state="normal")
        self.txt.delete("1.0", "end")

        if not self.entries:
            self.txt.insert("end", "  No entries found in this file.\n", "dim")
            self.lbl_count.config(text="0 entries", fg=TEXT_DIM)
            self.txt.config(state="disabled")
            return

        count = len(self.entries)
        self.lbl_count.config(text=f"{count} entr{'y' if count == 1 else 'ies'}",
                               fg=NEON_CYAN)

        # Column header
        col_hdr = (f"  {'#':<4}  {'OPERATOR':<22}  "
                   f"{'ORG':<22}  {'CREATED':<22}  HASH\n")
        self.txt.insert("end", col_hdr, "hdr")
        self.txt.insert("end", "  " + "─" * 90 + "\n", "dim")

        entry_tag = "ok" if verified is True else \
                    "err" if verified is False else "dim"

        for i, entry in enumerate(self.entries, 1):
            op      = entry.get("operator", "?")
            org     = entry.get("org",      "?")
            created = entry.get("created",  "?")
            h       = entry.get("hash",     "?")
            line    = f"  {i:<4}  {op:<22}  {org:<22}  {created:<22}  {h}\n"
            self.txt.insert("end", line, entry_tag)

        # Summary footer
        self.txt.insert("end", "\n")
        if verified is True:
            self.txt.insert("end",
                "  ✓  File HMAC verified — this audit trail is authentic.\n"
                "     Key A (in file) + Key B (auditor) → HMAC matches.\n",
                "ok")
        elif verified is False:
            self.txt.insert("end",
                "  ✗  HMAC mismatch.\n"
                "     Either Key B is incorrect, or the file has been tampered with.\n",
                "err")
        else:
            self.txt.insert("end",
                "  —  No HMAC verification performed.\n"
                "     Entries listed for reference only.\n",
                "dim")

        self.txt.config(state="disabled")


# ─── ENTRY POINT ─────────────────────────────────────────────────────────────
if __name__ == "__main__":
    app = RTFAudit()
    app.mainloop()
