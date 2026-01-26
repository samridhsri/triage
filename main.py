from llm import route_input
from notion import write_to_notion
from config import NOTION_TASKS_DB

test_item = {
    "type": "Task",
    "title": "Hello from Triage",
    "structured_fields": {},
    "next_step": "Confirm Notion write works",
    "confidence": 0.9,
}

write_to_notion(test_item, "Raw test input")


# if not isinstance(items, list):
#     raise Exception("LLM output is not a list")

# for item in items:
#     if not item.get("next_step"):
#         raise Exception("Rejected: missing next_step")
#     if item.get("confidence", 0) < 0.3:
#         item["structured_fields"]["Needs Review"] = True

#     write_to_notion(item, user_input)
