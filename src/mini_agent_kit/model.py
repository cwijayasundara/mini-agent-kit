"""The model protocol every provider implements."""

from typing import Protocol

from mini_agent_kit.types import Message, ModelReply, ToolSchema


class Model(Protocol):
    def complete(
        self, messages: list[Message], tools: list[ToolSchema]
    ) -> ModelReply: ...
