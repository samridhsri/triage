import os
import subprocess
import tkinter as tk

from feedback import is_feedback_enabled, set_feedback_enabled

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
MAIN_PY    = os.path.join(SCRIPT_DIR, "main.py")
VENV_PY    = os.path.join(SCRIPT_DIR, "myenv", "Scripts", "python.exe")

# ── Design tokens ────────────────────────────────────────────────────────────
BG      = "#0C0C0C"   # near-black background
SURFACE = "#141414"   # slightly lifted surface (unused but kept for extension)
BORDER  = "#1F1F1F"   # 1-px frame border
ACCENT  = "#6366F1"   # indigo-500 – primary accent
TEXT    = "#E8E8E8"   # primary text
MUTED   = "#383838"   # placeholder text
HINT    = "#2E2E2E"   # very subtle hint labels
FONT    = "Segoe UI"

PLACEHOLDER = "capture a task, project, or idea…"
WIN_W, WIN_H = 640, 108

# ── Logic ────────────────────────────────────────────────────────────────────
def submit():
    raw = entry.get("1.0", tk.END).strip()
    if raw and raw != PLACEHOLDER:
        subprocess.Popen(
            [VENV_PY, MAIN_PY, raw],
            cwd=SCRIPT_DIR,
            creationflags=subprocess.CREATE_NEW_CONSOLE | subprocess.CREATE_NEW_PROCESS_GROUP,
        )
    root.destroy()

def on_return(event):
    submit()
    return "break"

def clear_placeholder(_):
    if entry.get("1.0", tk.END).strip() == PLACEHOLDER:
        entry.delete("1.0", tk.END)
        entry.config(fg=TEXT)

def restore_placeholder(_):
    if not entry.get("1.0", tk.END).strip():
        entry.config(fg=MUTED)
        entry.insert("1.0", PLACEHOLDER)

def toggle_feedback():
    current = is_feedback_enabled()
    set_feedback_enabled(not current)
    update_fb_btn_text()

def update_fb_btn_text():
    enabled = is_feedback_enabled()
    fb_var.set("fb: ON" if enabled else "fb: OFF")
    fb_btn.config(fg=ACCENT if enabled else HINT)

# ── Window ───────────────────────────────────────────────────────────────────
root = tk.Tk()
root.overrideredirect(True)          # frameless
root.attributes("-topmost", True)
root.attributes("-alpha", 0.0)       # start transparent for fade-in
root.config(bg=BORDER)               # border colour peeks through 1-px gap

sw, sh = root.winfo_screenwidth(), root.winfo_screenheight()
root.geometry(f"{WIN_W}x{WIN_H}+{(sw - WIN_W) // 2}+{sh // 3}")

# ── Body (sits 1px inside the root border) ───────────────────────────────────
body = tk.Frame(root, bg=BG)
body.pack(fill="both", expand=True, padx=1, pady=1)

# ── Header row ───────────────────────────────────────────────────────────────
hdr = tk.Frame(body, bg=BG)
hdr.pack(fill="x", padx=20, pady=(12, 0))

tk.Label(
    hdr, text="triage",
    font=(FONT, 8, "bold"), bg=BG, fg=ACCENT,
).pack(side="left")

right_hdr = tk.Frame(hdr, bg=BG)
right_hdr.pack(side="right")

fb_var = tk.StringVar()
fb_btn = tk.Button(
    right_hdr,
    textvariable=fb_var,
    font=(FONT, 8, "bold"),
    bg=BG,
    fg=ACCENT,
    activebackground=BG,
    activeforeground=TEXT,
    relief="flat",
    bd=0,
    command=toggle_feedback,
    cursor="hand2",
)
fb_btn.pack(side="left", padx=(0, 15))

tk.Label(
    right_hdr, text="↵  send     esc  close",
    font=(FONT, 8), bg=BG, fg=HINT,
).pack(side="left")

update_fb_btn_text()

# ── Thin divider ─────────────────────────────────────────────────────────────
tk.Frame(body, bg=BORDER, height=1).pack(fill="x", pady=(10, 0))

# ── Input ────────────────────────────────────────────────────────────────────
entry = tk.Text(
    body,
    height=2,
    font=(FONT, 12),
    bg=BG,
    fg=MUTED,
    insertbackground=ACCENT,
    relief="flat",
    bd=0,
    wrap="word",
    padx=20,
    pady=10,
    selectbackground=ACCENT,
    selectforeground="#FFFFFF",
    spacing1=0,
    spacing2=2,
    spacing3=0,
)
entry.pack(fill="both", expand=True)
entry.insert("1.0", PLACEHOLDER)

entry.bind("<FocusIn>",  clear_placeholder)
entry.bind("<FocusOut>", restore_placeholder)
entry.bind("<Return>",   on_return)
entry.focus_set()

root.bind("<Escape>", lambda e: root.destroy())

# ── Drag-to-reposition (from header) ─────────────────────────────────────────
def _press(e): root._x0, root._y0 = e.x_root, e.y_root
def _drag(e):
    root.geometry(
        f"+{root.winfo_x() + e.x_root - root._x0}"
        f"+{root.winfo_y() + e.y_root - root._y0}"
    )
    root._x0, root._y0 = e.x_root, e.y_root

for widget in [hdr, *hdr.winfo_children()]:
    widget.bind("<Button-1>", _press)
    widget.bind("<B1-Motion>", _drag)

# ── Fade-in ───────────────────────────────────────────────────────────────────
def fade_in():
    a = root.attributes("-alpha")
    if a < 1.0:
        root.attributes("-alpha", min(a + 0.12, 1.0))
        root.after(12, fade_in)

root.after(10, fade_in)
root.mainloop()
