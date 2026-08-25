import sqlite3
from pathlib import Path


DATABASE_PATH = (
    Path(__file__).resolve().parents[2]
    / "data"
    / "threat_intelligence.db"
)


def get_connection() -> sqlite3.Connection:
    DATABASE_PATH.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    connection = sqlite3.connect(DATABASE_PATH)

    connection.row_factory = sqlite3.Row

    return connection


def initialize_database() -> None:
    connection = get_connection()

    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS indicators (
            id INTEGER PRIMARY KEY AUTOINCREMENT,

            indicator TEXT NOT NULL,
            indicator_type TEXT NOT NULL,

            threat_level TEXT NOT NULL,

            source TEXT NOT NULL,

            confidence REAL NOT NULL,

            description TEXT,

            created_at TEXT NOT NULL,

            UNIQUE(indicator, indicator_type)
        )
        """
    )

    connection.commit()
    connection.close()