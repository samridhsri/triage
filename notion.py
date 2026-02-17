import logging
import os

from notion_client import Client
import requests

from config import NOTION_TOKEN
from schema import INTENT_SCHEMA

logger = logging.getLogger(__name__)
notion = Client(auth=NOTION_TOKEN)

DB_MAP = {
    intent_type: os.getenv(schema["db_env_key"])
    for intent_type, schema in INTENT_SCHEMA.items()
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
    schema = INTENT_SCHEMA[item_type]
    fields = item.get("structured_fields", {})
    props = {schema["title_field"]: title_prop(item["title"])}

    for prop_name, spec in schema["properties"].items():
        prop_type = spec["type"]

        if "default" in spec:
            value = spec["default"]
        elif "field" in spec:
            value = fields.get(spec["field"])
        elif spec.get("source") == "raw_input":
            value = raw_input
        else:
            continue

        if value is None:
            continue

        if prop_type == "status":
            props[prop_name] = {"status": {"name": value}}
        elif prop_type == "select":
            props[prop_name] = select_prop(value)
        elif prop_type == "multi_select":
            props[prop_name] = multi_select_prop(value)
        elif prop_type == "date":
            props[prop_name] = date_prop(value)
        elif prop_type == "rich_text":
            props[prop_name] = rich_text_prop(value)

    return props


