from notion_client import Client
import requests

from config import (
    NOTION_TOKEN,
    NOTION_TASKS_DB,
    NOTION_PROJECTS_DB,
    NOTION_IDEAS_DB,
    NOTION_REMINDERS_DB,
)

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
    props = build_properties(item_type, item, raw_input)

    notion.pages.create(
        parent={"database_id": db_id},
        properties=props,
    )

# def build_properties(item_type, item, raw_input):
#     base = {
#         "Raw Input": rich_text_prop(raw_input)
#     }

#     # Task
#     if item_type == "Task":
#         base.update({
#             "Title": title_prop(item["title"]),
#             "Status": status_prop("Todo"),
#             "Priority": multi_select_prop(
#                 item["structured_fields"].get("priority")
#             ),
#             "Due Date": date_prop(
#                 item["structured_fields"].get("due_date")
#             ),
#             "Next Step": rich_text_prop(item["next_step"]),
#             "Confidence": number_prop(item["confidence"]),
#         })


#     # Project
#     elif item_type == "Project":
#         base.update({
#             "Goal": title_prop(item["title"]),
#             "Success Criteria": rich_text_prop(
#                 item["structured_fields"].get("success_criteria", "")
#             ),
#             "Review Frequency": select_prop(
#                 item["structured_fields"].get("review_frequency")
#             ),
#         })

#     # Idea
#     elif item_type == "Idea":
#         base.update({
#             "Idea": title_prop(item["title"]),
#             "Category": select_prop(
#                 item["structured_fields"].get("category")
#             ),
#             "Potential Impact": select_prop(
#                 item["structured_fields"].get("potential_impact")
#             ),
#             "Next Thinking Step": rich_text_prop(item["next_step"]),
#             "Confidence": number_prop(item["confidence"]),
#         })

#     # Reminder
#     elif item_type == "Reminder":
#         base.update({
#             "Reminder": title_prop(item["title"]),
#             "Trigger Date": date_prop(item["structured_fields"].get("trigger_date")),
#             "Urgency": select_prop(
#                 item["structured_fields"].get("urgency")
#             ),
#         })

#     return base


def build_properties(item_type, item, raw_input):
    if item_type != "Task":
        raise Exception(f"Unsupported type: {item_type}")

    props = {
        "Name": {
            "title": [
                {
                    "text": {
                        "content": item["title"]
                    }
                }
            ]
        },
        "Raw Input": {
            "rich_text": [
                {
                    "text": {
                        "content": raw_input
                    }
                }
            ]
        },
        "Status": {
            "status": {
                "name": "Todo"
            }
        },
        "Source": {
            "select": {
                "name": "AI"
            }
        }
    }

    # Priority (multi-select)
    priority = item.get("structured_fields", {}).get("priority")
    if priority:
        props["Priority"] = {
            "multi_select": [
                {"name": priority}
            ]
        }

    # Due date (ISO string: YYYY-MM-DD)
    due_date = item.get("structured_fields", {}).get("due_date")
    if due_date:
        props["Due date"] = {
            "date": {
                "start": due_date
            }
        }

    return props


