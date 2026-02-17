import re

INTENT_SCHEMA = {
    "Task": {
        "db_env_key":  "TASKS_DB_ID",
        "title_field": "Name",
        "properties": {
            "Status":    {"type": "status",       "default": "Todo"},
            "Source":    {"type": "select",        "default": "AI"},
            "Priority":  {"type": "multi_select",  "field": "priority"},
            "Due date":  {"type": "date",          "field": "due_date"},
            "Raw Input": {"type": "rich_text",     "source": "raw_input"},
        },
        "valid_fields": {
            "priority": {"allowed": {"High", "Medium", "Low"}, "nullable": True},
            "due_date": {"pattern": r"^\d{4}-\d{2}-\d{2}$",   "nullable": True},
        },
    },
    "Project": {
        "db_env_key":  "PROJECTS_DB_ID",
        "title_field": "Goal",
        "properties": {
            "Success Criteria": {"type": "rich_text", "field": "success_criteria"},
            "Review Frequency": {"type": "select",    "field": "review_frequency"},
        },
        "valid_fields": {
            "review_frequency": {"allowed": {"Weekly", "Monthly"}, "nullable": True},
            "success_criteria": {"nullable": True},
        },
    },
    "Idea": {
        "db_env_key":  "IDEAS_DB_ID",
        "title_field": "Idea",
        "properties": {
            "Category":         {"type": "multi_select", "field": "category"},
            "Potential Impact":  {"type": "select",      "field": "potential_impact"},
        },
        "valid_fields": {
            "category":         {"nullable": True},
            "potential_impact": {"allowed": {"High", "Medium", "Low"}, "nullable": True},
        },
    },
}
