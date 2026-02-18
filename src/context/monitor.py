"""Context monitoring module for tracking and visualizing context metrics."""

import asyncio
from collections import defaultdict
from datetime import datetime
from typing import Any

from pydantic import BaseModel


class AgentExecutionMetrics(BaseModel):
    """Metrics for agent execution performance.

    Attributes:
        agent_name: Name of the agent.
        execution_time_ms: Execution time in milliseconds.
        tokens_used: Tokens consumed during execution.
        memory_kb: Memory usage in kilobytes.
        timestamp: Timestamp of the execution.
    """

    agent_name: str
    execution_time_ms: float
    tokens_used: int
    memory_kb: int
    timestamp: datetime


class MemoryTierMetrics(BaseModel):
    """Metrics for memory usage by tier.

    Attributes:
        tier_name: Name of the memory tier (e.g., 'hot', 'warm', 'cold').
        tokens: Number of tokens in this tier.
        items: Number of items stored in this tier.
    """

    tier_name: str
    tokens: int
    items: int


class ContextMonitorMetrics(BaseModel):
    """Comprehensive metrics for context monitoring.

    Attributes:
        total_tokens: Total tokens in context.
        context_reduction_ratio: Ratio of context reduction (0.0 to 1.0).
        cache_hit_rate: Cache hit rate percentage (0.0 to 1.0).
        agent_execution_time: Mapping of agent names to execution times.
        memory_usage_by_tier: Mapping of tier names to token counts.
        timestamp: Timestamp of metrics collection.
    """

    total_tokens: int
    context_reduction_ratio: float
    cache_hit_rate: float
    agent_execution_time: dict[str, float]
    memory_usage_by_tier: dict[str, int]
    timestamp: datetime


class DashboardChart(BaseModel):
    """Dashboard chart configuration.

    Attributes:
        type: Chart type (line, bar, pie).
        data: Data key for the chart.
        title: Chart title.
    """

    type: str
    data: str
    title: str


class DashboardSummary(BaseModel):
    """Summary statistics for the dashboard.

    Attributes:
        total_sessions: Total number of sessions tracked.
        active_sessions: Number of currently active sessions.
        total_tokens_processed: Total tokens processed across all sessions.
        average_reduction_ratio: Average context reduction ratio.
        cache_efficiency: Overall cache efficiency percentage.
    """

    total_sessions: int
    active_sessions: int
    total_tokens_processed: int
    average_reduction_ratio: float
    cache_efficiency: float


class ContextMonitor:
    """Monitor and track context metrics with dashboard capabilities.

    This class provides functionality for recording, tracking, and visualizing
    context-related metrics including token usage, cache performance, and
    agent execution times.
    """

    def __init__(self, max_history_size: int = 1000) -> None:
        """Initialize the context monitor.

        Args:
            max_history_size: Maximum number of metric records to keep per session.
        """
        self._metrics: dict[str, list[ContextMonitorMetrics]] = defaultdict(list)
        self._max_history_size = max_history_size
        self._cache_hits: dict[str, int] = defaultdict(int)
        self._cache_misses: dict[str, int] = defaultdict(int)
        self._agent_calls: dict[str, int] = defaultdict(int)
        self._lock = asyncio.Lock()

    async def record_metrics(self, session_id: str, metrics: ContextMonitorMetrics) -> None:
        """Record metrics for a specific session.

        Args:
            session_id: Unique identifier for the session.
            metrics: The metrics to record.
        """
        async with self._lock:
            session_metrics = self._metrics[session_id]
            session_metrics.append(metrics)

            # Enforce max history size
            if len(session_metrics) > self._max_history_size:
                session_metrics.pop(0)

    async def record_cache_hit(self, session_id: str) -> None:
        """Record a cache hit for a session.

        Args:
            session_id: Unique identifier for the session.
        """
        async with self._lock:
            self._cache_hits[session_id] += 1

    async def record_cache_miss(self, session_id: str) -> None:
        """Record a cache miss for a session.

        Args:
            session_id: Unique identifier for the session.
        """
        async with self._lock:
            self._cache_misses[session_id] += 1

    async def record_agent_call(self, agent_name: str) -> None:
        """Record an agent call.

        Args:
            agent_name: Name of the agent being called.
        """
        async with self._lock:
            self._agent_calls[agent_name] += 1

    async def get_dashboard(self, session_id: str) -> dict[str, Any]:
        """Get dashboard data for a specific session.

        Args:
            session_id: Unique identifier for the session.

        Returns:
            Dictionary containing charts configuration and summary data.
        """
        async with self._lock:
            session_metrics = list(self._metrics.get(session_id, []))
            session_hits = self._cache_hits.get(session_id, 0)
            session_misses = self._cache_misses.get(session_id, 0)

        tokens_over_time = [
            {"timestamp": m.timestamp.isoformat(), "tokens": m.total_tokens}
            for m in session_metrics
        ]

        memory_by_tier: dict[str, int] = defaultdict(int)
        agent_distribution: dict[str, int] = defaultdict(int)
        for metric in session_metrics:
            for tier, count in metric.memory_usage_by_tier.items():
                memory_by_tier[tier] += count
            for agent_name in metric.agent_execution_time:
                agent_distribution[agent_name] += 1

        return {
            "charts": [
                {
                    "type": "line",
                    "data": "tokens_over_time",
                    "title": "Tokens Over Time",
                    "series": tokens_over_time,
                },
                {
                    "type": "bar",
                    "data": "memory_by_tier",
                    "title": "Memory Usage by Tier",
                    "series": [
                        {"tier": tier, "tokens": count} for tier, count in memory_by_tier.items()
                    ],
                },
                {
                    "type": "pie",
                    "data": "agent_calls",
                    "title": "Agent Call Distribution (Session)",
                    "series": [
                        {"agent": agent, "calls": count}
                        for agent, count in agent_distribution.items()
                    ],
                },
            ],
            "summary": await self._get_summary(
                session_id,
                preloaded=session_metrics,
                hits=session_hits,
                misses=session_misses,
            ),
        }

    async def _get_summary(
        self,
        session_id: str,
        preloaded: list[ContextMonitorMetrics] | None = None,
        hits: int | None = None,
        misses: int | None = None,
    ) -> DashboardSummary:
        """Generate summary statistics for a session.

        Args:
            session_id: Unique identifier for the session.
            preloaded: Optional preloaded metrics to avoid duplicate locking.
            hits: Optional preloaded hit count.
            misses: Optional preloaded miss count.

        Returns:
            Dashboard summary with aggregated statistics.
        """
        if preloaded is None or hits is None or misses is None:
            async with self._lock:
                session_metrics = list(self._metrics.get(session_id, []))
                hits = self._cache_hits.get(session_id, 0)
                misses = self._cache_misses.get(session_id, 0)
                total_sessions = len(self._metrics)
        else:
            session_metrics = preloaded
            async with self._lock:
                total_sessions = len(self._metrics)

        total_tokens = sum(m.total_tokens for m in session_metrics)
        avg_reduction = (
            sum(m.context_reduction_ratio for m in session_metrics) / len(session_metrics)
            if session_metrics
            else 0.0
        )

        safe_hits = hits or 0
        safe_misses = misses or 0
        cache_efficiency = safe_hits / (safe_hits + safe_misses) if (safe_hits + safe_misses) > 0 else 0.0

        return DashboardSummary(
            total_sessions=total_sessions,
            active_sessions=1 if session_metrics else 0,
            total_tokens_processed=total_tokens,
            average_reduction_ratio=avg_reduction,
            cache_efficiency=cache_efficiency,
        )

    async def get_session_metrics(self, session_id: str) -> list[ContextMonitorMetrics]:
        """Get all metrics for a specific session.

        Args:
            session_id: Unique identifier for the session.

        Returns:
            List of metrics for the session.
        """
        async with self._lock:
            metrics = self._metrics.get(session_id)
            return metrics.copy() if metrics else []

    async def get_all_sessions(self) -> list[str]:
        """Get list of all session IDs.

        Returns:
            List of session identifiers.
        """
        async with self._lock:
            return list(self._metrics.keys())

    async def clear_session(self, session_id: str) -> None:
        """Clear all metrics for a specific session.

        Args:
            session_id: Unique identifier for the session.
        """
        async with self._lock:
            if session_id in self._metrics:
                del self._metrics[session_id]
            if session_id in self._cache_hits:
                del self._cache_hits[session_id]
            if session_id in self._cache_misses:
                del self._cache_misses[session_id]

    async def get_cache_stats(self, session_id: str) -> dict[str, Any]:
        """Get cache statistics for a session.

        Args:
            session_id: Unique identifier for the session.

        Returns:
            Dictionary with cache hit/miss statistics.
        """
        async with self._lock:
            hits = self._cache_hits.get(session_id, 0)
            misses = self._cache_misses.get(session_id, 0)

        total = hits + misses
        return {
            "hits": hits,
            "misses": misses,
            "total": total,
            "hit_rate": hits / total if total > 0 else 0.0,
        }

    async def get_agent_stats(self) -> dict[str, int]:
        """Get agent call statistics.

        Returns:
            Dictionary mapping agent names to call counts.
        """
        async with self._lock:
            return dict(self._agent_calls)

    async def get_global_summary(self) -> dict[str, Any]:
        """Get global summary across all sessions.

        Returns:
            Dictionary with aggregated statistics.
        """
        async with self._lock:
            total_sessions = len(self._metrics)
            all_metrics = [m for metrics in self._metrics.values() for m in metrics]
            total_hits = sum(self._cache_hits.values())
            total_misses = sum(self._cache_misses.values())

        total_tokens = sum(m.total_tokens for m in all_metrics)
        all_reductions = [m.context_reduction_ratio for m in all_metrics]
        avg_reduction = (
            sum(all_reductions) / len(all_reductions) if all_reductions else 0.0
        )

        global_cache_efficiency = (
            total_hits / (total_hits + total_misses) if (total_hits + total_misses) > 0 else 0.0
        )

        return {
            "total_sessions": total_sessions,
            "total_tokens_processed": total_tokens,
            "average_reduction_ratio": avg_reduction,
            "global_cache_efficiency": global_cache_efficiency,
            "agent_calls": await self.get_agent_stats(),
        }
