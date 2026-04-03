"""Task/reminder management — auto-generated from meeting notes."""

import json
import re
from datetime import datetime
from pathlib import Path


TASKS_FILENAME = "tasks.json"


def _load_tasks(output_dir: Path) -> list[dict]:
    tasks_path = output_dir / TASKS_FILENAME
    if tasks_path.exists():
        return json.loads(tasks_path.read_text())
    return []


def _save_tasks(output_dir: Path, tasks: list[dict]):
    tasks_path = output_dir / TASKS_FILENAME
    tasks_path.write_text(json.dumps(tasks, indent=2))


def extract_action_items(notes_text: str, meeting_id: str, meeting_date: str) -> list[dict]:
    """Parse action items from meeting notes markdown.

    Looks for the '## Action Items' section and extracts bulleted items.
    """
    items = []
    in_action_items = False

    for line in notes_text.split("\n"):
        stripped = line.strip()

        # Detect section headers
        if stripped.lower().startswith("## action items"):
            in_action_items = True
            continue
        elif stripped.startswith("## "):
            in_action_items = False
            continue

        if not in_action_items:
            continue

        # Parse bullet points
        if stripped.startswith(("- ", "* ", "• ")):
            text = stripped.lstrip("-*• ").strip()
            if not text:
                continue

            # Try to extract owner and deadline
            owner = ""
            deadline = ""

            # Look for patterns like "John:" or "**John**:" at the start
            owner_match = re.match(r'^(?:\*\*)?([A-Z][a-z]+(?:\s[A-Z][a-z]+)?)(?:\*\*)?\s*[:—-]\s*(.*)', text)
            if owner_match:
                owner = owner_match.group(1)
                text = owner_match.group(2)

            # Look for deadline patterns
            deadline_patterns = [
                r'\bby\s+((?:Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday|tomorrow|end of (?:week|day|month)|next week|EOD|EOW|\w+\s+\d{1,2}(?:st|nd|rd|th)?))\b',
                r'\bdue\s+([\w\s]+?)(?:\.|$)',
                r'\bdeadline:\s*([\w\s]+?)(?:\.|$)',
            ]
            for pattern in deadline_patterns:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    deadline = match.group(1).strip()
                    break

            items.append({
                "id": f"{meeting_id}_{len(items)}",
                "text": text,
                "owner": owner,
                "deadline": deadline,
                "meeting_id": meeting_id,
                "meeting_date": meeting_date,
                "status": "pending",
                "created": datetime.now().isoformat(),
            })

    return items


def add_tasks_from_meeting(output_dir: Path, notes_text: str,
                           meeting_id: str, meeting_date: str) -> list[dict]:
    """Extract action items from notes and add them to the task list."""
    tasks = _load_tasks(output_dir)
    new_items = extract_action_items(notes_text, meeting_id, meeting_date)

    # Remove old tasks from the same meeting (in case of re-processing)
    tasks = [t for t in tasks if t.get("meeting_id") != meeting_id]

    tasks.extend(new_items)

    # Sort: pending first, then by creation date (newest first)
    tasks.sort(key=lambda t: (
        0 if t["status"] == "pending" else 1 if t["status"] == "in_progress" else 2,
        t.get("created", ""),
    ), reverse=False)

    _save_tasks(output_dir, tasks)
    return new_items


def get_all_tasks(output_dir: Path) -> list[dict]:
    return _load_tasks(output_dir)


def get_pending_tasks(output_dir: Path) -> list[dict]:
    return [t for t in _load_tasks(output_dir) if t["status"] in ("pending", "in_progress")]


def update_task_status(output_dir: Path, task_id: str, new_status: str):
    """Update a task's status: 'pending', 'in_progress', 'completed'."""
    tasks = _load_tasks(output_dir)
    for task in tasks:
        if task["id"] == task_id:
            task["status"] = new_status
            if new_status == "completed":
                task["completed_at"] = datetime.now().isoformat()
            break
    _save_tasks(output_dir, tasks)


def delete_task(output_dir: Path, task_id: str):
    tasks = _load_tasks(output_dir)
    tasks = [t for t in tasks if t["id"] != task_id]
    _save_tasks(output_dir, tasks)
