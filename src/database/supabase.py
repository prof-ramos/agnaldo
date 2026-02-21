"""Supabase client wrapper for CRUD operations.

This module provides a SupabaseClient class that wraps the supabase-py library
with CRUD methods, pagination support, and custom error handling.
"""

from threading import Lock
from typing import Any, TypeVar

from loguru import logger
from supabase import Client, create_client

from src.config.settings import get_settings
from src.exceptions import DatabaseError, SupabaseConnectionError

T = TypeVar("T")
DEFAULT_PAGE_SIZE = 1000


def _safe_payload_details(data: dict[str, Any] | None) -> dict[str, Any]:
    """Return non-sensitive payload metadata for error details."""
    if not data:
        return {"payload_keys": [], "payload_size": 0}
    return {"payload_keys": sorted(data.keys()), "payload_size": len(data)}


class SupabaseClient:
    """Supabase client wrapper with safe synchronous CRUD operations.

    This class provides a high-level interface to Supabase with:
    - CRUD operations over supabase-py
    - Pagination controls
    - Custom error handling with domain-specific exceptions
    - Type-safe operations using generics

    Attributes:
        client: The underlying Supabase client instance
        url: Supabase project URL
        key: Supabase service role key

    Example:
        >>> client = SupabaseClient()
        >>> result = client.create("users", {"discord_id": "123"})
    """

    def __init__(self, url: str | None = None, key: str | None = None) -> None:
        """Initialize the Supabase client.

        Args:
            url: Supabase project URL. Defaults to settings.SUPABASE_URL.
            key: Supabase service role key. Defaults to settings.SUPABASE_SERVICE_ROLE_KEY.

        Raises:
            SupabaseConnectionError: If client initialization fails.
        """
        settings = get_settings()
        self.url = url or settings.SUPABASE_URL
        self.key = key or settings.SUPABASE_SERVICE_ROLE_KEY

        try:
            self._client: Client = create_client(self.url, self.key)
            logger.info(f"Supabase client initialized: {self.url[:30]}...")
        except Exception as e:
            logger.error(f"Failed to initialize Supabase client: {e}")
            raise SupabaseConnectionError(
                f"Failed to initialize Supabase client: {e}",
                status_code=getattr(e, "status", None),
                operation="init",
            ) from e

    @property
    def client(self) -> Client:
        """Get the underlying Supabase client."""
        return self._client

    def create(self, table: str, data: dict[str, Any]) -> dict[str, Any]:
        """Create a new record in the specified table.

        Args:
            table: The table name to insert into.
            data: The record data as a dictionary.

        Returns:
            The created record as returned by Supabase.

        Raises:
            DatabaseError: If the create operation fails.

        Example:
            >>> client.create("users", {"discord_id": "123", "username": "john"})
        """
        try:
            response = (
                self._client.table(table)
                .insert(data)
                .execute()
            )
            if response.data:
                return response.data[0]
            return {}
        except Exception as e:
            logger.error(f"Create failed on table '{table}': {e}")
            raise DatabaseError(
                f"Failed to create record in {table}: {e}",
                operation="create",
                details={"table": table, **_safe_payload_details(data)},
            ) from e

    def read(
        self,
        table: str,
        filters: dict[str, Any] | None = None,
        *,
        limit: int | None = None,
        offset: int | None = None,
        order: str | None = None,
    ) -> list[dict[str, Any]]:
        """Read records from the specified table.

        Args:
            table: The table name to read from.
            filters: Optional filter dictionary for WHERE clauses.
            limit: Maximum number of records to return.
            offset: Number of records to skip.
            order: Column name to order by (prefix with '-' for desc).

        Returns:
            List of records matching the criteria.

        Raises:
            DatabaseError: If the read operation fails.

        Example:
            >>> client.read("users", {"discord_id": "123"})
            >>> client.read("messages", limit=10, order="-created_at")
        """
        try:
            query = self._client.table(table).select("*")

            if filters:
                for column, value in filters.items():
                    query = query.eq(column, value)

            if order:
                if order.startswith("-"):
                    query = query.order(order[1:], desc=True)
                else:
                    query = query.order(order)

            if offset is not None:
                page_size = limit if limit is not None else DEFAULT_PAGE_SIZE
                query = query.range(offset, offset + page_size - 1)
            elif limit is not None:
                query = query.limit(limit)

            response = query.execute()
            return response.data or []
        except Exception as e:
            logger.error(f"Read failed on table '{table}': {e}")
            raise DatabaseError(
                f"Failed to read from {table}: {e}",
                operation="read",
                details={"table": table, "filters": filters, "limit": limit, "offset": offset},
            ) from e

    def read_by_id(self, table: str, record_id: str | int) -> dict[str, Any] | None:
        """Read a single record by its ID.

        Args:
            table: The table name to read from.
            record_id: The record's primary key value.

        Returns:
            The record if found, None otherwise.

        Raises:
            DatabaseError: If the read operation fails.

        Example:
            >>> client.read_by_id("users", "uuid-here")
        """
        try:
            response = (
                self._client.table(table)
                .select("*")
                .eq("id", record_id)
                .limit(1)
                .execute()
            )
            if response.data:
                return response.data[0]
            return None
        except Exception as e:
            logger.error(f"Read by ID failed on table '{table}': {e}")
            raise DatabaseError(
                f"Failed to read by ID from {table}: {e}",
                operation="read_by_id",
                details={"table": table, "id": record_id},
            ) from e

    def update(
        self,
        table: str,
        data: dict[str, Any],
        filters: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """Update records in the specified table.

        Args:
            table: The table name to update.
            data: The update data as a dictionary.
            filters: Filter dictionary for WHERE clauses.

        Returns:
            List of updated records.

        Raises:
            DatabaseError: If the update operation fails.

        Example:
            >>> client.update("users", {"username": "new_name"}, {"id": "uuid"})
        """
        try:
            if not filters:
                raise DatabaseError(
                    f"Refusing update on {table} without filters",
                    operation="update",
                    details={"table": table},
                )

            query = self._client.table(table).update(data)

            if filters:
                for column, value in filters.items():
                    query = query.eq(column, value)

            response = query.execute()
            return response.data or []
        except Exception as e:
            logger.error(f"Update failed on table '{table}': {e}")
            raise DatabaseError(
                f"Failed to update {table}: {e}",
                operation="update",
                details={"table": table, "filters": filters, **_safe_payload_details(data)},
            ) from e

    def update_by_id(
        self,
        table: str,
        record_id: str | int,
        data: dict[str, Any],
    ) -> dict[str, Any] | None:
        """Update a single record by its ID.

        Args:
            table: The table name to update.
            record_id: The record's primary key value.
            data: The update data as a dictionary.

        Returns:
            The updated record if found, None otherwise.

        Raises:
            DatabaseError: If the update operation fails.

        Example:
            >>> client.update_by_id("users", "uuid", {"username": "new_name"})
        """
        try:
            response = (
                self._client.table(table)
                .update(data)
                .eq("id", record_id)
                .execute()
            )
            if response.data:
                return response.data[0]
            return None
        except Exception as e:
            logger.error(f"Update by ID failed on table '{table}': {e}")
            raise DatabaseError(
                f"Failed to update by ID in {table}: {e}",
                operation="update_by_id",
                details={"table": table, "id": record_id, **_safe_payload_details(data)},
            ) from e

    def delete(
        self,
        table: str,
        filters: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """Delete records from the specified table.

        Args:
            table: The table name to delete from.
            filters: Filter dictionary for WHERE clauses.

        Returns:
            List of deleted records.

        Raises:
            DatabaseError: If the delete operation fails.

        Example:
            >>> client.delete("users", {"id": "uuid"})
        """
        try:
            if not filters:
                raise DatabaseError(
                    f"Refusing delete on {table} without filters",
                    operation="delete",
                    details={"table": table},
                )

            query = self._client.table(table).delete()

            if filters:
                for column, value in filters.items():
                    query = query.eq(column, value)

            response = query.execute()
            return response.data or []
        except Exception as e:
            logger.error(f"Delete failed on table '{table}': {e}")
            raise DatabaseError(
                f"Failed to delete from {table}: {e}",
                operation="delete",
                details={"table": table, "filters": filters},
            ) from e

    def delete_by_id(
        self,
        table: str,
        record_id: str | int,
    ) -> dict[str, Any] | None:
        """Delete a single record by its ID.

        Args:
            table: The table name to delete from.
            record_id: The record's primary key value.

        Returns:
            The deleted record if found, None otherwise.

        Raises:
            DatabaseError: If the delete operation fails.

        Example:
            >>> client.delete_by_id("users", "uuid")
        """
        try:
            response = (
                self._client.table(table)
                .delete()
                .eq("id", record_id)
                .execute()
            )
            if response.data:
                return response.data[0]
            return None
        except Exception as e:
            logger.error(f"Delete by ID failed on table '{table}': {e}")
            raise DatabaseError(
                f"Failed to delete by ID from {table}: {e}",
                operation="delete_by_id",
                details={"table": table, "id": record_id},
            ) from e

    def list(
        self,
        table: str,
        *,
        filters: dict[str, Any] | None = None,
        limit: int = 100,
        offset: int = 0,
        order: str | None = None,
    ) -> list[dict[str, Any]]:
        """List records with pagination support.

        Args:
            table: The table name to list from.
            filters: Optional filter dictionary for WHERE clauses.
            limit: Maximum number of records to return (default 100).
            offset: Number of records to skip (default 0).
            order: Column name to order by (prefix with '-' for desc).

        Returns:
            List of records.

        Raises:
            DatabaseError: If the list operation fails.

        Example:
            >>> client.list("users", limit=20, offset=10)
        """
        return self.read(table, filters, limit=limit, offset=offset, order=order)

    def count(
        self,
        table: str,
        filters: dict[str, Any] | None = None,
    ) -> int:
        """Count records matching the given filters.

        Args:
            table: The table name to count from.
            filters: Optional filter dictionary for WHERE clauses.

        Returns:
            Number of matching records.

        Raises:
            DatabaseError: If the count operation fails.

        Example:
            >>> client.count("users", {"is_active": True})
        """
        try:
            query = self._client.table(table).select("*", count="exact")

            if filters:
                for column, value in filters.items():
                    query = query.eq(column, value)

            response = query.execute()
            return response.count if response.count is not None else 0
        except Exception as e:
            logger.error(f"Count failed on table '{table}': {e}")
            raise DatabaseError(
                f"Failed to count from {table}: {e}",
                operation="count",
                details={"table": table, "filters": filters},
            ) from e

    def rpc(
        self,
        function_name: str,
        params: dict[str, Any] | None = None,
    ) -> Any:
        """Execute a Remote Procedure Call (RPC) function.

        Args:
            function_name: The name of the RPC function to call.
            params: Optional parameters for the RPC function.

        Returns:
            The RPC function result.

        Raises:
            DatabaseError: If the RPC call fails.

        Example:
            >>> client.rpc("match_documents", {"query_embedding": [0.1, 0.2, ...]})
        """
        try:
            response = self._client.rpc(function_name, params).execute()
            return response.data
        except Exception as e:
            logger.error(f"RPC call '{function_name}' failed: {e}")
            raise DatabaseError(
                f"Failed to execute RPC function '{function_name}': {e}",
                operation="rpc",
                details={"function": function_name, "params": params},
            ) from e


# Global client instance
_client: SupabaseClient | None = None
_client_lock = Lock()


def get_supabase_client() -> SupabaseClient:
    """Get the singleton Supabase client instance.

    Returns:
        SupabaseClient: The global Supabase client instance.
    """
    global _client
    if _client is None:
        with _client_lock:
            if _client is None:
                _client = SupabaseClient()
    return _client
