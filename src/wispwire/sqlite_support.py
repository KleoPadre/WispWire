"""SQLite feature checks required by the packet index."""

import sqlite3
from collections.abc import Callable
from dataclasses import dataclass


@dataclass(frozen=True)
class SqliteFeatureStatus:
    """Result of one SQLite feature check."""

    available: bool
    error: str | None


def check_fts5_trigram(
    connection_factory: Callable[[], sqlite3.Connection] | None = None,
) -> SqliteFeatureStatus:
    """Check FTS5 support with a case-insensitive trigram tokenizer."""
    factory = connection_factory or _open_memory_connection
    connection: sqlite3.Connection | None = None
    try:
        connection = factory()
        connection.execute(
            "CREATE VIRTUAL TABLE wispwire_fts_probe "
            "USING fts5(info, tokenize='trigram case_sensitive 0')"
        )
    except sqlite3.Error as error:
        return SqliteFeatureStatus(
            False, f"SQLite FTS5 trigram is unavailable: {error}"
        )
    finally:
        if connection is not None:
            connection.close()

    return SqliteFeatureStatus(True, None)


def _open_memory_connection() -> sqlite3.Connection:
    """Open a separate short-lived SQLite database for feature probing."""
    return sqlite3.connect(":memory:")
