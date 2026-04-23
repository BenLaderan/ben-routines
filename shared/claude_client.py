import os
import anthropic

_client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
_MODEL = "claude-haiku-4-5-20251001"


def ask(prompt: str) -> str:
    """Send a prompt to Claude and return the text response."""
    message = _client.messages.create(
        model=_MODEL,
        max_tokens=1024,
        messages=[{"role": "user", "content": prompt}],
    )
    return message.content[0].text
