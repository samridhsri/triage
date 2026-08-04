import json
import os
import sys
import tkinter as tk
from tkinter import ttk, messagebox
from feedback import is_feedback_enabled, set_feedback_enabled, log_feedback

# ── Design tokens ────────────────────────────────────────────────────────────
BG      = "#0C0C0C"   # near-black background
SURFACE = "#141414"   # surface panel
BORDER  = "#1F1F1F"   # frame border
ACCENT  = "#6366F1"   # indigo-500 – primary accent
TEXT    = "#E8E8E8"   # primary text
MUTED   = "#737373"   # secondary text
HINT    = "#404040"   # subtle hint labels
SUCCESS = "#22C55E"   # green success button
DANGER  = "#EF4444"   # red correction button
FONT    = "Segoe UI"


class FeedbackWindow:
    def __init__(self, raw_input: str, predicted_intents: list):
        self.raw_input = raw_input
        self.predicted_intents = predicted_intents
        self.result_intents = predicted_intents
        self.was_corrected = False

        self.root = tk.Tk()
        self.root.title("Triage - Intent Feedback")
        self.root.overrideredirect(True)
        self.root.attributes("-topmost", True)
        self.root.attributes("-alpha", 0.0)
        self.root.config(bg=BORDER)

        win_w, win_h = 680, 520
        sw, sh = self.root.winfo_screenwidth(), self.root.winfo_screenheight()
        self.root.geometry(f"{win_w}x{win_h}+{(sw - win_w) // 2}+{(sh - win_h) // 2}")

        self.body = tk.Frame(self.root, bg=BG)
        self.body.pack(fill="both", expand=True, padx=1, pady=1)

        self._build_header()
        self._build_content()
        self._build_footer()

        # Drag setup
        for widget in [self.hdr, *self.hdr.winfo_children()]:
            widget.bind("<Button-1>", self._press)
            widget.bind("<B1-Motion>", self._drag)

        self.root.bind("<Escape>", lambda e: self.on_close())
        self.fade_in()

    def _press(self, e):
        self.root._x0, self.root._y0 = e.x_root, e.y_root

    def _drag(self, e):
        self.root.geometry(
            f"+{self.root.winfo_x() + e.x_root - self.root._x0}"
            f"+{self.root.winfo_y() + e.y_root - self.root._y0}"
        )
        self.root._x0, self.root._y0 = e.x_root, e.y_root

    def fade_in(self):
        a = self.root.attributes("-alpha")
        if a < 1.0:
            self.root.attributes("-alpha", min(a + 0.15, 1.0))
            self.root.after(15, self.fade_in)

    def _build_header(self):
        self.hdr = tk.Frame(self.body, bg=BG)
        self.hdr.pack(fill="x", padx=20, pady=(14, 8))

        tk.Label(
            self.hdr, text="triage intent review",
            font=(FONT, 10, "bold"), bg=BG, fg=ACCENT,
        ).pack(side="left")

        # Feedback toggle button
        self.fb_status_var = tk.StringVar()
        self._update_toggle_label()

        self.toggle_btn = tk.Button(
            self.hdr,
            textvariable=self.fb_status_var,
            font=(FONT, 8, "bold"),
            bg=SURFACE,
            fg=TEXT,
            activebackground=BORDER,
            activeforeground=TEXT,
            relief="flat",
            bd=0,
            padx=8,
            pady=2,
            command=self.toggle_feedback_mode,
            cursor="hand2",
        )
        self.toggle_btn.pack(side="right")

        tk.Frame(self.body, bg=BORDER, height=1).pack(fill="x", pady=(4, 8))

    def _update_toggle_label(self):
        enabled = is_feedback_enabled()
        self.fb_status_var.set("Feedback Mode: ON" if enabled else "Feedback Mode: OFF")

    def toggle_feedback_mode(self):
        current = is_feedback_enabled()
        set_feedback_enabled(not current)
        self._update_toggle_label()

    def _build_content(self):
        container = tk.Frame(self.body, bg=BG)
        container.pack(fill="both", expand=True, padx=20, pady=5)

        # Raw input preview
        tk.Label(
            container, text="RAW INPUT:", font=(FONT, 8, "bold"), bg=BG, fg=MUTED
        ).pack(anchor="w", pady=(0, 2))

        input_box = tk.Label(
            container,
            text=f'"{self.raw_input}"',
            font=(FONT, 11, "italic"),
            bg=SURFACE,
            fg=TEXT,
            anchor="w",
            padx=12,
            pady=8,
            wraplength=620,
            justify="left",
        )
        input_box.pack(fill="x", pady=(0, 12))

        # Predicted intents
        tk.Label(
            container, text="CLASSIFIED INTENTS:", font=(FONT, 8, "bold"), bg=BG, fg=MUTED
        ).pack(anchor="w", pady=(0, 4))

        # Intent list editor / viewer
        self.intents_frame = tk.Frame(container, bg=BG)
        self.intents_frame.pack(fill="both", expand=True)

        self.intent_rows = []
        if not self.predicted_intents:
            no_intent_lbl = tk.Label(
                self.intents_frame,
                text="[No intents classified]",
                font=(FONT, 10),
                bg=SURFACE,
                fg=MUTED,
                pady=15,
            )
            no_intent_lbl.pack(fill="x")
        else:
            for idx, intent in enumerate(self.predicted_intents):
                self._create_intent_row(self.intents_frame, idx, intent)

        # Correction Notes Section
        notes_hdr = tk.Frame(container, bg=BG)
        notes_hdr.pack(fill="x", pady=(10, 2))
        tk.Label(
            notes_hdr, text="CORRECTION NOTES / INSTRUCTIONS (Optional):", font=(FONT, 8, "bold"), bg=BG, fg=MUTED
        ).pack(side="left")

        self.notes_entry = tk.Entry(
            container,
            font=(FONT, 10),
            bg=SURFACE,
            fg=TEXT,
            insertbackground=ACCENT,
            relief="flat",
            bd=0,
        )
        self.notes_entry.pack(fill="x", ipady=6, pady=(0, 10))

    def _create_intent_row(self, parent, idx, intent):
        row_frame = tk.Frame(parent, bg=SURFACE, highlightbackground=BORDER, highlightthickness=1)
        row_frame.pack(fill="x", pady=4, ipady=4, ipadx=6)

        # Type dropdown
        type_var = tk.StringVar(value=intent.get("type", "Task"))
        type_menu = ttk.OptionMenu(row_frame, type_var, intent.get("type", "Task"), "Task", "Project", "Idea")
        type_menu.config(width=8)
        type_menu.pack(side="left", padx=(6, 10))

        # Title entry
        title_var = tk.StringVar(value=intent.get("title", ""))
        title_entry = tk.Entry(
            row_frame,
            textvariable=title_var,
            font=(FONT, 10),
            bg=BG,
            fg=TEXT,
            insertbackground=ACCENT,
            relief="flat",
            bd=0,
        )
        title_entry.pack(side="left", fill="x", expand=True, padx=5, ipady=4)

        # Delete button
        del_btn = tk.Button(
            row_frame,
            text="✕",
            font=(FONT, 9, "bold"),
            bg=SURFACE,
            fg=DANGER,
            activebackground=BORDER,
            activeforeground=DANGER,
            relief="flat",
            bd=0,
            command=lambda: self._delete_intent_row(row_frame),
            cursor="hand2",
        )
        del_btn.pack(side="right", padx=6)

        self.intent_rows.append({
            "frame": row_frame,
            "type_var": type_var,
            "title_var": title_var,
            "original": intent,
        })

    def _delete_intent_row(self, frame):
        frame.destroy()
        self.intent_rows = [r for r in self.intent_rows if r["frame"].winfo_exists()]

    def _build_footer(self):
        footer = tk.Frame(self.body, bg=BG)
        footer.pack(fill="x", padx=20, pady=(10, 16))

        tk.Button(
            footer,
            text="✓ Looks Good",
            font=(FONT, 9, "bold"),
            bg=SUCCESS,
            fg="#FFFFFF",
            activebackground="#16A34A",
            activeforeground="#FFFFFF",
            relief="flat",
            bd=0,
            padx=16,
            pady=8,
            command=self.on_approve,
            cursor="hand2",
        ).pack(side="left")

        tk.Button(
            footer,
            text="Save Feedback & Continue",
            font=(FONT, 9, "bold"),
            bg=ACCENT,
            fg="#FFFFFF",
            activebackground="#4F46E5",
            activeforeground="#FFFFFF",
            relief="flat",
            bd=0,
            padx=16,
            pady=8,
            command=self.on_submit_feedback,
            cursor="hand2",
        ).pack(side="right")

    def on_approve(self):
        """User confirms classification is correct without edits."""
        self.was_corrected = False
        self.root.destroy()

    def on_submit_feedback(self):
        """User edited or submitted feedback/corrections."""
        corrected = []
        for row in self.intent_rows:
            if not row["frame"].winfo_exists():
                continue
            orig = row["original"].copy()
            orig["type"] = row["type_var"].get()
            orig["title"] = row["title_var"].get().strip()
            if orig["title"]:
                corrected.append(orig)

        notes = self.notes_entry.get().strip()
        log_feedback(
            raw_input=self.raw_input,
            predicted_intents=self.predicted_intents,
            corrected_intents=corrected,
            notes=notes,
        )
        self.result_intents = corrected
        self.was_corrected = True
        self.root.destroy()

    def on_close(self):
        self.root.destroy()

    def run(self):
        self.root.mainloop()
        return self.result_intents


def review_intents_interactive(raw_input: str, predicted_intents: list) -> list:
    """Helper to launch feedback window and return final (confirmed or corrected) intents."""
    app = FeedbackWindow(raw_input, predicted_intents)
    return app.run()


if __name__ == "__main__":
    test_input = "read chapter 5 and update project proposal by Friday"
    test_intents = [
        {"type": "Task", "title": "Read chapter 5", "priority": "High", "due_date": None},
        {"type": "Project", "title": "Update project proposal", "success_criteria": None},
    ]
    res = review_intents_interactive(test_input, test_intents)
    print("Final result intents:", json.dumps(res, indent=2))
