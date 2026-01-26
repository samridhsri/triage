from llm import route_input
from notion_client import AsyncClient
import os

notion = AsyncClient(auth=os.environ["NOTION_TOKEN"])

items = route_input(user_input)

if not isinstance(items, list):
    raise Exception("LLM output is not a list")

for item in items:
    if not item.get("next_step"):
        raise Exception("Rejected: missing next_step")
    if item.get("confidence", 0) < 0.3:
        item["structured_fields"]["Needs Review"] = True
