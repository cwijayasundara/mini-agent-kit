"""A live model backed by the Fireworks AI chat-completions API (stdlib only)."""

import json
import os
import urllib.error
import urllib.request
from collections.abc import Callable

from mini_agent_kit.types import Message, ModelReply, ToolCall, ToolSchema

DEFAULT_MODEL = "accounts/fireworks/models/glm-5p3-flash"
TEMPERATURE = 0
URL = "https://api.fireworks.ai/inference/v1/chat/completions"

Transport = Callable[[dict[str, object]], dict[str, object]]


class FireworksError(Exception):
    """The API call failed or returned something unusable."""


def encode_message(message: Message) -> dict[str, object]:
    """One kit Message in OpenAI chat format."""
    if message.role == "tool":
        return {
            "role": "tool",
            "tool_call_id": message.tool_call_id,
            "content": message.content,
        }
    encoded: dict[str, object] = {"role": message.role, "content": message.content}
    if message.tool_calls:
        encoded["tool_calls"] = [
            {
                "id": c.id,
                "type": "function",
                "function": {"name": c.name, "arguments": json.dumps(c.arguments)},
            }
            for c in message.tool_calls
        ]
    return encoded


def encode_tool(tool: ToolSchema) -> dict[str, object]:
    return {
        "type": "function",
        "function": {
            "name": tool["name"],
            "description": tool["description"],
            "parameters": tool["input_schema"],
        },
    }


def _parse_call(raw: dict[str, object]) -> ToolCall:
    fn = raw["function"]
    assert isinstance(fn, dict)
    arguments = json.loads(fn["arguments"] or "{}")
    if not isinstance(arguments, dict):
        raise FireworksError("tool arguments must be a JSON object")
    return ToolCall(str(raw["id"]), str(fn["name"]), arguments)


def parse_reply(body: dict[str, object]) -> ModelReply:
    """Turn a chat-completions response body into a ModelReply."""
    try:
        choices = body["choices"]
        assert isinstance(choices, list)
        message = choices[0]["message"]
        calls = message.get("tool_calls") or []
        if calls:
            return ModelReply(tool_calls=tuple(_parse_call(c) for c in calls))
        return ModelReply(final=message["content"] or "")
    except (KeyError, IndexError, AssertionError, TypeError, ValueError) as exc:
        raise FireworksError(f"unexpected response: {exc!r}") from exc


def _http_post(api_key: str) -> Transport:
    def post(payload: dict[str, object]) -> dict[str, object]:
        request = urllib.request.Request(
            URL,
            data=json.dumps(payload).encode(),
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=60) as response:
                data: dict[str, object] = json.load(response)
                return data
        except urllib.error.HTTPError as exc:
            raise FireworksError(f"HTTP {exc.code}: {exc.read().decode()}") from exc
        except urllib.error.URLError as exc:
            raise FireworksError(f"network error: {exc.reason}") from exc

    return post


class FireworksModel:
    def __init__(
        self,
        api_key: str | None = None,
        model: str = DEFAULT_MODEL,
        transport: Transport | None = None,
    ) -> None:
        key = api_key or os.environ.get("FIREWORKS_API_KEY")
        if transport is None:
            if not key:
                raise FireworksError("set FIREWORKS_API_KEY to use the live model")
            transport = _http_post(key)
        self._model = model
        self._post = transport

    def complete(self, messages: list[Message], tools: list[ToolSchema]) -> ModelReply:
        payload: dict[str, object] = {
            "model": self._model,
            "messages": [encode_message(m) for m in messages],
            "tools": [encode_tool(t) for t in tools],
            "temperature": TEMPERATURE,
        }
        return parse_reply(self._post(payload))
