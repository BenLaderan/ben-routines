import os
import anthropic

_client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
_MODEL = "claude-3-5-haiku-20241022"


def ask(prompt: str, max_tokens: int = 3000) -> str:
    """Send a prompt to Claude and return the text response."""
    message = _client.messages.create(
        model=_MODEL,
        max_tokens=max_tokens,
        messages=[{"role": "user", "content": prompt}],
    )
    return message.content[0].text
