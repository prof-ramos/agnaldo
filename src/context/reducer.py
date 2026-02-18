"""Context reduction module for managing token limits."""

from enum import Enum
from typing import Any

from tiktoken import encoding_for_model


class ContextMode(str, Enum):
    """Context reduction modes."""

    FULL = "full"
    COMPACT = "compact"
    SUMMARY = "summary"


class ContextReducer:
    """Reduces context messages to fit within token limits."""

    def __init__(self, model: str = "gpt-4o") -> None:
        """Initialize the reducer with a specific model encoding.

        Args:
            model: Model name for tokenization (default: gpt-4o)
        """
        try:
            self.encoding = encoding_for_model(model)
        except Exception as exc:
            raise ValueError(
                f"Unsupported model for tokenizer encoding: {model}. "
                "Configure a valid OpenAI model name."
            ) from exc
        self._model = model

    def count_tokens(self, messages: list[dict[str, Any]]) -> int:
        """Count tokens in a list of messages.

        Args:
            messages: List of message dictionaries with 'role' and 'content'

        Returns:
            Total token count
        """
        total = 0
        for message in messages:
            content = message.get("content", "")
            if isinstance(content, str):
                total += len(self.encoding.encode(content))
            elif isinstance(content, list):
                # Handle multimodal content (e.g., images + text)
                for item in content:
                    if isinstance(item, dict) and "text" in item:
                        total += len(self.encoding.encode(item["text"]))
        return total

    def reduce(
        self,
        messages: list[dict[str, Any]],
        mode: ContextMode = ContextMode.FULL,
        max_tokens: int = 8000,
    ) -> list[dict[str, Any]]:
        """Reduce context messages to fit within max_tokens.

        Args:
            messages: List of message dictionaries
            mode: Reduction strategy (full/compact/summary)
            max_tokens: Maximum tokens to keep

        Returns:
            Reduced list of messages
        """
        if mode == ContextMode.FULL:
            return self._reduce_full(messages, max_tokens)
        elif mode == ContextMode.COMPACT:
            return self._reduce_compact(messages, max_tokens)
        elif mode == ContextMode.SUMMARY:
            return self._reduce_summary(messages, max_tokens)
        return messages

    def _reduce_full(
        self, messages: list[dict[str, Any]], max_tokens: int
    ) -> list[dict[str, Any]]:
        """Keep most recent messages within token limit."""
        result: list[dict[str, Any]] = []
        current_tokens = 0

        for message in reversed(messages):
            tokens = self._count_message_tokens(message)
            if current_tokens + tokens <= max_tokens:
                result.insert(0, message)
                current_tokens += tokens
            else:
                break

        return result

    def _reduce_compact(
        self, messages: list[dict[str, Any]], max_tokens: int
    ) -> list[dict[str, Any]]:
        """Compact messages by removing redundant content."""
        result: list[dict[str, Any]] = []
        current_tokens = 0

        for message in messages:
            compacted = self._compact_message(message)
            tokens = self._count_message_tokens(compacted)
            if current_tokens + tokens <= max_tokens:
                result.append(compacted)
                current_tokens += tokens
            else:
                break

        return result

    def _reduce_summary(
        self, messages: list[dict[str, Any]], max_tokens: int
    ) -> list[dict[str, Any]]:
        """Keep only system messages and recent user/assistant messages."""
        system_messages = [m for m in messages if m.get("role") == "system"]
        conversation = [m for m in messages if m.get("role") != "system"]

        trimmed_system: list[dict[str, Any]] = []
        system_tokens = 0
        for msg in reversed(system_messages):
            msg_tokens = self._count_message_tokens(msg)
            if system_tokens + msg_tokens <= max_tokens:
                trimmed_system.insert(0, msg)
                system_tokens += msg_tokens
            else:
                break

        result: list[dict[str, Any]] = []
        current_tokens = system_tokens

        result.extend(trimmed_system)
        preserved_conversation: list[dict[str, Any]] = []

        for message in reversed(conversation):
            tokens = self._count_message_tokens(message)
            if current_tokens + tokens <= max_tokens:
                preserved_conversation.append(message)
                current_tokens += tokens
            else:
                break

        result.extend(reversed(preserved_conversation))
        return result

    def _count_message_tokens(self, message: dict[str, Any]) -> int:
        """Count tokens in a single message."""
        content = message.get("content", "")
        if isinstance(content, str):
            return len(self.encoding.encode(content))
        elif isinstance(content, list):
            total = 0
            for item in content:
                if isinstance(item, dict) and "text" in item:
                    total += len(self.encoding.encode(item["text"]))
            return total
        return 0

    def _compact_message(self, message: dict[str, Any]) -> dict[str, Any]:
        """Remove whitespace and redundant content from a message."""
        content = message.get("content", "")
        if isinstance(content, str):
            # Remove excessive whitespace while preserving structure
            compacted = " ".join(content.split())
            return {**message, "content": compacted}
        return message
