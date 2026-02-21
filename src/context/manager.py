"""Context Manager integration for token tracking and offloading.

This module provides the central ContextManager that integrates:
- Token counting and tracking
- Context reduction when over limits
- Intelligent offloading to cache
- Metrics monitoring
"""

import asyncio
from datetime import datetime, timezone
from typing import Any

from loguru import logger

from src.context.monitor import ContextMonitor, ContextMonitorMetrics
from src.context.offloading import ContextOffloading
from src.context.reducer import ContextMode, ContextReducer


class ContextManager:
    """Central manager for context tracking, reduction, and offloading.

    This class coordinates all context-related operations:
    - Tracks token usage per session
    - Automatically reduces context when over limits
    - Offloads old messages to cache
    - Monitors and reports metrics

    Attributes:
        max_tokens: Maximum tokens allowed in context.
        reducer: Context reducer for token optimization.
        offloading: Cache manager for offloaded content.
        monitor: Metrics tracker.
        sessions: Active context sessions.
    """

    def __init__(
        self,
        max_tokens: int = 8000,
        offloading_maxsize: int = 100,
        enable_monitoring: bool = True,
    ) -> None:
        """Initialize the ContextManager.

        Args:
            max_tokens: Maximum tokens allowed per context.
            offloading_maxsize: Max size for offloading cache.
            enable_monitoring: Whether to enable metrics monitoring.
        """
        self.max_tokens = max_tokens
        self.reducer = ContextReducer(model="gpt-4o")
        self.offloading = ContextOffloading(maxsize=offloading_maxsize)
        self.monitor = ContextMonitor() if enable_monitoring else None

        # Active sessions
        self.sessions: dict[str, dict[str, Any]] = {}
        self._sessions_lock = asyncio.Lock()

    async def create_session(
        self,
        session_id: str,
        user_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Create a new context session.

        Args:
            session_id: Unique session identifier.
            user_id: User ID for the session.
            metadata: Optional session metadata.
        """
        async with self._sessions_lock:
            self.sessions[session_id] = {
                "session_id": session_id,
                "user_id": user_id,
                "messages": [],
                "offloaded_keys": [],
                "created_at": datetime.now(timezone.utc),
                "metadata": metadata or {},
                "token_count": 0,
            }

        if self.monitor:
            await self.monitor.record_agent_call("context_manager")

        logger.debug(f"Created context session: {session_id}")

    async def add_message(
        self,
        session_id: str,
        role: str,
        content: str,
        auto_reduce: bool = True,
    ) -> int:
        """Add a message to the session context.

        Args:
            session_id: Session identifier.
            role: Message role (user, assistant, system).
            content: Message content.
            auto_reduce: Whether to auto-reduce when over limit.

        Returns:
            Current token count after adding.

        Raises:
            ValueError: If session doesn't exist.
        """
        needs_reduction = False
        async with self._sessions_lock:
            session = self.sessions.get(session_id)
            if not session:
                raise ValueError(f"Session not found: {session_id}")

            message = {"role": role, "content": content}
            session["messages"].append(message)

            # Count tokens
            session["token_count"] = self._count_tokens(session["messages"])

            # Auto-reduce if over limit
            if auto_reduce and session["token_count"] > self.max_tokens:
                needs_reduction = True

        if needs_reduction:
            await self._reduce_context(session_id, mode=ContextMode.SUMMARY)

        async with self._sessions_lock:
            session = self.sessions.get(session_id)
            if not session:
                raise ValueError(f"Session not found: {session_id}")

            # Record metrics
            if self.monitor:
                metrics = ContextMonitorMetrics(
                    total_tokens=session["token_count"],
                    context_reduction_ratio=0.0,
                    cache_hit_rate=0.0,
                    agent_execution_time={},
                    memory_usage_by_tier={},
                    timestamp=datetime.now(timezone.utc),
                )
                await self.monitor.record_metrics(session_id, metrics)

            return int(session["token_count"])

    async def get_context(
        self,
        session_id: str,
        include_offloaded: bool = False,
    ) -> list[dict[str, Any]]:
        """Get the current context for a session.

        Args:
            session_id: Session identifier.
            include_offloaded: Whether to include offloaded content.

        Returns:
            List of messages in the context.
        """
        async with self._sessions_lock:
            session = self.sessions.get(session_id)
            if not session:
                return []

            context = list(session["messages"])
            offloaded_keys = list(session["offloaded_keys"])

        # Include offloaded content if requested (outside lock to avoid blocking)
        if include_offloaded and offloaded_keys:
            for key in offloaded_keys:
                content = await self.offloading.load_on_demand(key)
                if content and self.monitor:
                    await self.monitor.record_cache_hit(session_id)
                elif self.monitor:
                    await self.monitor.record_cache_miss(session_id)

                if content:
                    context.append(
                        {
                            "role": "system",
                            "content": f"[Offloaded context retrieved: {content[:200]}...]",
                        }
                    )

        return context

    async def summarize_session(
        self,
        session_id: str,
        max_summary_tokens: int = 500,
    ) -> str:
        """Summarize a session's conversation.

        Args:
            session_id: Session identifier.
            max_summary_tokens: Max tokens for the summary.

        Returns:
            Summary text.
        """
        async with self._sessions_lock:
            session = self.sessions.get(session_id)
            if not session:
                return ""
            messages = list(session["messages"])

        # Get messages and create a simple summary
        if not messages:
            return "Empty session"

        # Count messages by type
        user_messages = sum(1 for m in messages if m["role"] == "user")
        assistant_messages = sum(1 for m in messages if m["role"] == "assistant")

        # Get first and last messages
        first_user = next((m["content"] for m in messages if m["role"] == "user"), None)
        last_assistant = next(
            (m["content"] for m in reversed(messages) if m["role"] == "assistant"),
            None,
        )

        summary_parts = [
            f"Session with {user_messages} user messages, {assistant_messages} assistant responses",
            f"Started: {first_user[:100] if first_user else 'N/A'}...",
            f"Latest response: {last_assistant[:100] if last_assistant else 'N/A'}...",
        ]

        return " | ".join(summary_parts)

    async def offload_old_messages(
        self,
        session_id: str,
        keep_recent: int = 5,
    ) -> int:
        """Offload old messages to cache.

        Args:
            session_id: Session identifier.
            keep_recent: Number of recent messages to keep in context.

        Returns:
            Number of messages offloaded.
        """
        async with self._sessions_lock:
            session = self.sessions.get(session_id)
            if not session:
                return 0

            messages = session["messages"]
            if len(messages) <= keep_recent:
                return 0

            # Offload old messages
            to_offload = messages[:-keep_recent]
            messages[:] = messages[-keep_recent:]

            # Update token count
            session["token_count"] = self._count_tokens(messages)

        generated_keys: list[str] = []
        for i, msg in enumerate(to_offload):
            key = f"{session_id}_offload_{i}_{datetime.now(timezone.utc).isoformat()}"
            await self.offloading.offload(
                key,
                f"{msg['role']}: {msg['content']}",
                priority=0,
            )
            generated_keys.append(key)

        async with self._sessions_lock:
            session = self.sessions.get(session_id)
            if not session:
                return 0
            session["offloaded_keys"].extend(generated_keys)
            offloaded_count = len(generated_keys)

            logger.info(f"Offloaded {offloaded_count} messages from session {session_id}")
            return offloaded_count

    async def get_session_stats(self, session_id: str) -> dict[str, Any]:
        """Get statistics for a session.

        Args:
            session_id: Session identifier.

        Returns:
            Dictionary with session statistics.
        """
        async with self._sessions_lock:
            session = self.sessions.get(session_id)
            if not session:
                return {"session_id": session_id, "exists": False}

            return {
                "session_id": session_id,
                "user_id": session["user_id"],
                "message_count": len(session["messages"]),
                "token_count": session["token_count"],
                "offloaded_count": len(session["offloaded_keys"]),
                "created_at": session["created_at"].isoformat(),
                "exists": True,
            }

    async def close_session(self, session_id: str) -> None:
        """Close and cleanup a session.

        Args:
            session_id: Session identifier.
        """
        async with self._sessions_lock:
            if session_id in self.sessions:
                del self.sessions[session_id]
                logger.debug(f"Closed context session: {session_id}")

    async def _reduce_context(
        self,
        session_id: str,
        mode: ContextMode = ContextMode.SUMMARY,
    ) -> None:
        """Reduce context using the specified mode.

        Args:
            session_id: Session identifier.
            mode: Reduction mode to use.
        """
        async with self._sessions_lock:
            session = self.sessions.get(session_id)
            if not session:
                return

            original_count = len(session["messages"])
            original_tokens = session["token_count"]

            # Use reducer to trim messages
            session["messages"] = self.reducer.reduce(
                session["messages"],
                mode=mode,
                max_tokens=int(self.max_tokens * 0.8),  # Leave some headroom
            )

            session["token_count"] = self._count_tokens(session["messages"])
            reduced_count = len(session["messages"])
            reduced_tokens = session["token_count"]

        reduction_ratio = 1.0 - (reduced_tokens / original_tokens) if original_tokens > 0 else 0.0

        logger.info(
            f"Reduced context for {session_id}: "
            f"{original_count} -> {reduced_count} messages, "
            f"{original_tokens} -> {reduced_tokens} tokens "
            f"({reduction_ratio:.1%} reduction)"
        )

    def _count_tokens(self, messages: list[dict[str, Any]]) -> int:
        """Count tokens in a list of messages.

        Args:
            messages: List of message dictionaries.

        Returns:
            Total token count.
        """
        return self.reducer.count_tokens(messages)

    async def get_monitoring_dashboard(self, session_id: str) -> dict[str, Any] | None:
        """Get monitoring dashboard data for a session.

        Args:
            session_id: Session identifier.

        Returns:
            Dashboard data or None if monitoring disabled.
        """
        if not self.monitor:
            return None
        return await self.monitor.get_dashboard(session_id)


# Global context manager instance
_context_manager: ContextManager | None = None
_context_manager_lock = asyncio.Lock()


async def get_context_manager(
    max_tokens: int = 8000,
    offloading_maxsize: int = 100,
    enable_monitoring: bool = True,
) -> ContextManager:
    """Get or create the global ContextManager instance.

    Args:
        max_tokens: Maximum tokens per context.
        offloading_maxsize: Max cache size.
        enable_monitoring: Enable metrics monitoring.

    Returns:
        The ContextManager instance.
    """
    global _context_manager

    async with _context_manager_lock:
        if _context_manager is None:
            _context_manager = ContextManager(
                max_tokens=max_tokens,
                offloading_maxsize=offloading_maxsize,
                enable_monitoring=enable_monitoring,
            )
        else:
            mismatches: list[str] = []
            if _context_manager.max_tokens != max_tokens:
                mismatches.append(
                    f"max_tokens(existing={_context_manager.max_tokens}, requested={max_tokens})"
                )
            existing_offloading_size = _context_manager.offloading._maxsize
            if existing_offloading_size != offloading_maxsize:
                mismatches.append(
                    "offloading_maxsize("
                    f"existing={existing_offloading_size}, requested={offloading_maxsize})"
                )
            existing_monitoring = _context_manager.monitor is not None
            if existing_monitoring != enable_monitoring:
                mismatches.append(
                    f"enable_monitoring(existing={existing_monitoring}, requested={enable_monitoring})"
                )
            if mismatches:
                logger.warning(
                    "get_context_manager called with different parameters after initialization: "
                    + ", ".join(mismatches)
                )

    return _context_manager
