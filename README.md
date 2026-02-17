# Triage

A hotkey-triggered capture tool. Press **Ctrl + Alt + T**, type anything, hit **Enter** — Triage classifies your input as a Task, Project, or Idea and writes it to the right Notion database automatically.

---

## Prerequisites

| Tool | Notes |
| --- | --- |
| Python 3.10+ | [python.org](https://python.org) |
| AutoHotkey v2 | [autohotkey.com](https://www.autohotkey.com) — for the global hotkey |
| Google AI Studio account | Free — for the Gemini API key |
| Notion account | Free — workspace + integration token |

---

## Setup

### 1. Install Python dependencies

```sh
python -m venv myenv
myenv\Scripts\activate
pip install -r requirements.txt
pip install google-genai
```

### 2. Get your API keys

#### Gemini (Google AI Studio)

1. Go to [aistudio.google.com](https://aistudio.google.com)
2. Click **Get API key** → **Create API key**
3. Copy the key — you'll put it in `.env` as `GEMINI_API_KEY`

#### Notion

1. Go to [notion.so/my-integrations](https://www.notion.so/my-integrations)
2. Click **New integration** → give it a name (e.g. `Triage`) → Submit
3. Copy the **Internal Integration Secret** — this is your `NOTION_TOKEN`

### 3. Create your Notion databases

See the **[Notion Workspace Structure](#notion-workspace-structure)** section below for the exact fields each database needs.

Once your databases exist, get each database ID from the URL:

```text
notion.so/your-workspace/THIS-IS-THE-DATABASE-ID?v=...
```

It's the 32-character string between the last `/` and the `?`.

Then **share each database with your integration**: open the database → click `...` menu → **Connections** → add your integration.

### 4. Create the `.env` file

Create a file named `.env` in the project root:

```env
GEMINI_API_KEY=your_gemini_key_here

NOTION_TOKEN=secret_your_notion_token_here
TASKS_DB_ID=your_tasks_database_id
PROJECTS_DB_ID=your_projects_database_id
IDEAS_DB_ID=your_ideas_database_id
REMINDERS_DB_ID=
```

`REMINDERS_DB_ID` can be left empty — it's reserved for future use.

### 5. Set up the hotkey

Open `triage.ahk` and update the path on line 4 to match where you cloned the project:

```autohotkey
Run('python "C:\your\path\to\Triage\ui.py"')
```

Then double-click `triage.ahk` to run it (AutoHotkey must be installed). You'll see it appear in the system tray. To have it start automatically, add a shortcut to your Windows Startup folder (`Win + R` → `shell:startup`).

---

## Usage

1. Press **Ctrl + Alt + T** anywhere
2. Type what's on your mind — you can mix multiple things in one sentence
3. Press **Enter** — the window closes and Triage processes your input in the background
4. Check your Notion databases — items appear within a few seconds

Examples of what you can say:

- `"email the contractor by Friday and look into switching to Cloudflare"` → 2 Tasks
- `"build a personal finance tracker"` → Project
- `"serverless functions might be cheaper at scale"` → Idea
- `"submit invoice tomorrow high priority, also idea: dark mode for the app"` → Task + Idea

---

## Notion Workspace Structure

Create three separate databases in Notion with exactly these property names and types.

### Tasks

| Property | Type | Notes |
| --- | --- | --- |
| `Name` | Title | Task title |
| `Status` | Status | Needs options: **Todo**, In Progress, Done |
| `Priority` | Multi-select | Options: **High**, **Medium**, **Low** |
| `Due date` | Date | |
| `Raw Input` | Text | The original sentence you typed |
| `Source` | Select | Options: **AI**, Manual |

### Projects

| Property | Type | Notes |
| --- | --- | --- |
| `Goal` | Title | Project title |
| `Success Criteria` | Text | |
| `Review Frequency` | Select | Options: **Weekly**, **Monthly** |

### Ideas

| Property | Type | Notes |
| --- | --- | --- |
| `Idea` | Title | Idea title |
| `Category` | Multi-select | Triage infers this — add options as needed |
| `Potential Impact` | Select | Options: **High**, **Medium**, **Low** |

> Property names are case-sensitive and must match exactly — the code writes to them by name.

---

## Troubleshooting

### Nothing appears in Notion

- Check `triage.log` in the project folder for error details
- Make sure each database is shared with your integration (Connections menu)
- Double-check the database IDs in `.env` — they should be 32 characters, no hyphens

### `ModuleNotFoundError: google`

- Run `pip install google-genai` inside your virtual environment

### Hotkey doesn't work

- Make sure AutoHotkey v2 is installed (not v1)
- Check that `triage.ahk` is running in the system tray
- Verify the file path in `triage.ahk` is correct for your machine
