import os
import ssl

import anthropic
import certifi
import httpx

# Fix SSL on macOS — ensure httpx (used by anthropic SDK) can find certificates
os.environ.setdefault("SSL_CERT_FILE", certifi.where())
os.environ.setdefault("REQUESTS_CA_BUNDLE", certifi.where())

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
    """Send transcript to Claude and return structured meeting notes as markdown."""
    # Create client with explicit SSL certificate bundle for macOS compatibility
    http_client = httpx.Client(
        verify=certifi.where(),
    )
    client = anthropic.Anthropic(api_key=api_key, http_client=http_client)

    # For very short transcripts, adjust expectations
    word_count = len(transcript.split())
    user_message = f"Here is the meeting transcript ({word_count} words):\n\n{transcript}"

    if word_count < 50:
        user_message += "\n\nNote: This is a very short transcript. Provide brief notes accordingly."

    print(f"Sending transcript to Claude ({model})...")

    message = client.messages.create(
        model=model,
        max_tokens=4096,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_message}],
    )

    notes = message.content[0].text
    print("Meeting notes generated.")
    return notes
