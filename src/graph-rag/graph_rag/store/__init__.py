"""Graph storage. Only this package may import duckdb."""

from graph_rag.store.duckdb_store import DuckDBGraphStore

__all__ = ["DuckDBGraphStore"]
