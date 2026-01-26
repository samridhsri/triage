import os
from dotenv import load_dotenv

load_dotenv()

NOTION_TOKEN = os.getenv("NOTION_TOKEN")
NOTION_TASKS_DB = os.getenv("TASKS_DB_ID")
NOTION_PROJECTS_DB = os.getenv("PROJECTS_DB_ID")
NOTION_IDEAS_DB = os.getenv("IDEAS_DB_ID")
NOTION_REMINDERS_DB = os.getenv("REMINDERS_DB_ID")

LLM_API_KEY = os.getenv("LLM_API_KEY")
