# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this project does

Hotkey-triggered capture tool. **Ctrl+Alt+T** opens a floating Tkinter window; user types anything and hits Enter; `ui.py` spawns `main.py` as a background subprocess that classifies the input via Gemini and writes structured items to Notion databases (Tasks, Projects, Ideas).

## Commands

The virtual environment is a Windows venv at `myenv/` (invoked as `myenv/Scripts/python.exe` on Windows, which is how AHK and `ui.py` call it).

```sh
# Run tests (all tests are embedded in main.py)
python -m pytest main.py -v
python -m unittest main -v

# Run a single test class
python -m unittest main.TestValidateTask -v

# Manually trigger triage on an input string
python main.py "email recruiter and push the commit"

# Flush the dead-letter queue (retry failed Notion writes)
python main.py --flush

# Run the LLM evaluation suite (makes real Gemini API calls, ~100 cases)
python evaluation/eval.py
python evaluation/eval.py --real-only      # only the 16 real-world cases
python evaluation/eval.py --tag task       # filter by tag (task/project/idea/multi-intent/no-op/etc.)

# Install dependencies
pip install -r requirements.txt
pip install google-genai
```

## Architecture

### Pipeline (the critical path)

```
ui.py (Tkinter popup)
  └─ subprocess: main.py "<raw text>"
       ├─ llm.split_intents()          # Gemini 2.5 Flash → list of typed intent dicts
       ├─ main._validate_intent()      # schema-validated, rejects bad/unknown fields
       └─ notion.write_to_notion()     # writes to Notion DB, retries 429/5xx, DLQ on failure
```

### Key design: `schema.py` is the single source of truth

`INTENT_SCHEMA` in `schema.py` drives everything — it maps each intent type (`Task`, `Project`, `Idea`) to:
- which env var holds the database ID (`db_env_key`)
- which Notion property is the title (`title_field`)
- how each property maps to an LLM field or a hardcoded default (`properties`)
- what values are valid for each LLM field (`valid_fields`)

Both `main._validate_intent()` and `notion.build_properties()` read from this schema. Adding a new field means updating `INTENT_SCHEMA` only.

### Dead-letter queue

`notion.py` catches all Notion write failures and appends them to `dead_letter.jsonl` (one JSON object per line). `main.flush_dead_letter()` replays them — cleared before replay so failures re-append themselves.

### Raw input log

Every call to `main.py "<input>"` appends a timestamped entry to `raw_inputs.jsonl`. This accumulates real usage data for expanding `evaluation/cases.json` over time.

### Files

| File | Role |
|---|---|
| `schema.py` | `INTENT_SCHEMA` — single source of truth for all intent types |
| `main.py` | Pipeline orchestration + all unit tests |
| `llm.py` | Gemini API wrapper; `split_intents()` is the active path; `route_input()` is legacy Phase 1 (unused) |
| `notion.py` | Notion writes with retry logic and dead-letter fallback |
| `config.py` | Loads `.env` into named constants |
| `ui.py` | Tkinter floating input window; spawns `main.py` as subprocess |
| `splitter_prompt.txt` | Active LLM system prompt for intent splitting/classification |
| `router_prompt.txt` | Legacy Phase 1 router prompt (not called in current flow) |
| `triage.ahk` | AutoHotkey v2 script that binds Ctrl+Alt+T → launches `ui.py` |
| `evaluation/cases.json` | 100-case golden dataset (16 real, 84 synthetic) |
| `evaluation/eval.py` | Eval runner: calls `split_intents()` and scores against golden cases |
| `raw_inputs.jsonl` | Append-only log of every raw input (created at runtime) |

### `.env` variables

```
GEMINI_API_KEY       # Google AI Studio key (used by llm.py)
NOTION_TOKEN         # Notion integration secret
TASKS_DB_ID          # 32-char Notion database ID, no hyphens
PROJECTS_DB_ID
IDEAS_DB_ID
REMINDERS_DB_ID      # reserved, can be empty
TEST_DB_ID           # optional, for test writes
```

### LLM contract

`split_intents()` sends `splitter_prompt.txt` + `"TODAY: YYYY-MM-DD\n\nUSER INPUT: ..."` to Gemini 2.5 Flash and expects a JSON object `{"intents": [...]}`. `_extract_json()` in `llm.py` strips markdown code fences that Gemini sometimes adds. All fields for irrelevant types must be `null` (not omitted) per the prompt — the validator in `main.py` uses `intent.get(field)` which returns `None` for missing keys too, so both are safe.

### Notion property names are case-sensitive

The property names in `INTENT_SCHEMA["properties"]` keys (e.g. `"Due date"`, `"Raw Input"`, `"Potential Impact"`) must exactly match the column names in the Notion databases. `validate_notion_schemas()` is called at startup to catch mismatches.
