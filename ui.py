import os
import subprocess
import tkinter as tk

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
MAIN_PY = os.path.join(SCRIPT_DIR, "main.py")
VENV_PYTHON = os.path.join(SCRIPT_DIR, "myenv", "Scripts", "python.exe")


def submit():
    text = entry.get("1.0", tk.END).strip()
    if text:
        subprocess.Popen(
            [VENV_PYTHON, MAIN_PY, text],
            cwd=SCRIPT_DIR,
            creationflags=subprocess.CREATE_NEW_CONSOLE | subprocess.CREATE_NEW_PROCESS_GROUP,
        )
    root.destroy()


def on_return(event):
    submit()
    return "break"


root = tk.Tk()
root.title("Triage")
root.geometry("500x120")
root.attributes("-topmost", True)

entry = tk.Text(root, height=3, font=("Segoe UI", 11))
entry.pack(padx=10, pady=10, fill="both")

entry.focus_set()

entry.bind("<Return>", on_return)
root.bind("<Escape>", lambda e: root.destroy())

root.mainloop()
