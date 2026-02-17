import logging

from notion_client import Client
import requests

from config import (
    NOTION_TOKEN,
    NOTION_TASKS_DB,
    NOTION_PROJECTS_DB,
    NOTION_IDEAS_DB,
    NOTION_REMINDERS_DB,
)

logger = logging.getLogger(__name__)
notion = Client(auth=NOTION_TOKEN)

DB_MAP = {
    "Task": NOTION_TASKS_DB,
    "Project": NOTION_PROJECTS_DB,
    "Idea": NOTION_IDEAS_DB,
    "Reminder": NOTION_REMINDERS_DB,
}

# ---------- Helpers to format properties ----------

def title_prop(text):
    return {"title": [{"text": {"content": text}}]}

def rich_text_prop(text):
    return {"rich_text": [{"text": {"content": text}}]}

def select_prop(name):
    if not name:
        return None
    return {"select": {"name": name}}

def number_prop(val):
    return {"number": val}

def status_prop(value):
    return {"status": {"name": value}} if value else None

def multi_select_prop(values):
    if not values:
        return None
    if isinstance(values, str):
        values = [values]
    return {
        "multi_select": [{"name": v} for v in values]
    }


def date_prop(date_str):
    if not date_str:
        return None
    return {"date": {"start": date_str}}



# ---------- Write a routed item to Notion ----------

def write_to_notion(item, raw_input):
    item_type = item["type"]
    if item_type not in DB_MAP:
        raise Exception(f"Unsupported type: {item_type}")

    db_id = DB_MAP[item_type]
    if not db_id:
        logger.warning('%s not written (DB not configured): "%s"', item_type, item["title"])
        return

    props = build_properties(item_type, item, raw_input)

    notion.pages.create(
        parent={"database_id": db_id},
        properties=props,
    )
    logger.info('Notion write OK: %s "%s"', item_type, item["title"])

def build_properties(item_type, item, raw_input):
    fields = item.get("structured_fields", {})

    if item_type == "Task":
        props = {
            "Name": title_prop(item["title"]),
            "Raw Input": rich_text_prop(raw_input),
            "Status": {"status": {"name": "Todo"}},
            "Source": select_prop("AI"),
        }
        priority = fields.get("priority")
        if priority:
            props["Priority"] = multi_select_prop(priority)
        due_date = fields.get("due_date")
        if due_date:
            props["Due date"] = date_prop(due_date)
        return props

    if item_type == "Project":
        props = {
            "Goal": title_prop(item["title"]),
        }
        success_criteria = fields.get("success_criteria")
        if success_criteria:
            props["Success Criteria"] = rich_text_prop(success_criteria)
        review_frequency = fields.get("review_frequency")
        if review_frequency:
            props["Review Frequency"] = select_prop(review_frequency)
        return props

    if item_type == "Idea":
        props = {
            "Idea": title_prop(item["title"]),
        }
        category = fields.get("category")
        if category:
            props["Category"] = multi_select_prop(category)
        potential_impact = fields.get("potential_impact")
        if potential_impact:
            props["Potential Impact"] = select_prop(potential_impact)
        return props

    raise Exception(f"Unsupported type: {item_type}")


