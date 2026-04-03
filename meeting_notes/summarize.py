import json
import subprocess

SYSTEM_PROMPT = """You are a meeting notes assistant. Given a transcript of a meeting, produce structured notes in markdown format with these exact sections:

## Summary
A concise 3-5 sentence overview of the meeting — what was discussed, the general tone, and the outcome.

## Key Decisions
A bulleted list of decisions that were made during the meeting. If no clear decisions were made, state that.

## Action Items
A bulleted list of next steps or tasks. For each item, include:
- The person responsible (if identifiable from the transcript)
- A clear description of what needs to be done
- Any mentioned deadline or timeframe

## Open Questions
A bulleted list of unresolved topics, questions raised but not answered, or items deferred to a future discussion.

Be concise and factual. Only include information that is clearly present in the transcript.
Do not speculate or add information not discussed. If speakers are not identifiable by name, describe them by role or context if possible."""


def generate_notes(transcript: str, api_key: str,
                   model: str = "claude-sonnet-4-20250514") -> str:
    """Send transcript to Claude via curl (bypasses Python SSL issues on macOS)."""
    word_count = len(transcript.split())
    user_message = f"Here is the meeting transcript ({word_count} words):\n\n{transcript}"

    if word_count < 50:
        user_message += "\n\nNote: This is a very short transcript. Provide brief notes accordingly."

    print(f"Sending transcript to Claude ({model})...")

    payload = json.dumps({
        "model": model,
        "max_tokens": 4096,
        "system": SYSTEM_PROMPT,
        "messages": [{"role": "user", "content": user_message}],
    })

    result = subprocess.run(
        [
            "curl", "-s",
            "https://api.anthropic.com/v1/messages",
            "-H", f"x-api-key: {api_key}",
            "-H", "content-type: application/json",
            "-H", "anthropic-version: 2023-06-01",
            "-d", payload,
        ],
        capture_output=True,
        text=True,
        timeout=120,
    )

    if result.returncode != 0:
        raise RuntimeError(f"curl failed: {result.stderr}")

    response = json.loads(result.stdout)

    if response.get("type") == "error":
        error_msg = response.get("error", {}).get("message", "Unknown API error")
        raise RuntimeError(f"Claude API error: {error_msg}")

    notes = response["content"][0]["text"]
    print("Meeting notes generated.")
    return notes
