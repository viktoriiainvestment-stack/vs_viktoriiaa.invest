"""Shared Anthropic client + small helpers used by analysis.py and extract.py."""
import base64
import os

import anthropic

CLAUDE_API_KEY = os.environ.get("CLAUDE_API_KEY")
CLAUDE_MODEL = os.environ.get("CLAUDE_MODEL", "claude-sonnet-5")

_client = anthropic.Anthropic(api_key=CLAUDE_API_KEY) if CLAUDE_API_KEY else None


def is_configured():
    return _client is not None


def ask(system, user_text, max_tokens=1500):
    if not _client:
        raise RuntimeError("CLAUDE_API_KEY не налаштовано.")
    response = _client.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=max_tokens,
        system=system,
        messages=[{"role": "user", "content": user_text}],
    )
    return response.content[0].text


def ask_with_image(system, user_text, image_bytes, mime_type, max_tokens=700):
    if not _client:
        raise RuntimeError("CLAUDE_API_KEY не налаштовано.")
    response = _client.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=max_tokens,
        system=system,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": mime_type,
                            "data": base64.b64encode(image_bytes).decode("ascii"),
                        },
                    },
                    {"type": "text", "text": user_text},
                ],
            }
        ],
    )
    return response.content[0].text
