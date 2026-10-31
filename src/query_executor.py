
import sqlite3
from pathlib import Path
from urllib.parse import quote

from src.sql_validator import validate_sql


def execute_query(
    db_path: str | Path,
    query: str,
    allowed_tables: set[str],
    max_rows: int = 500,
) -> list[dict]:
    path = Path(db_path).resolve()

    if not path.is_file():
        raise FileNotFoundError("The database has not been initialized.")

    safe_query = validate_sql(query, allowed_tables)

    uri = f"file:{quote(str(path))}?mode=ro"
    connection = sqlite3.connect(uri, uri=True)
    connection.row_factory = sqlite3.Row

    def authorize(action, arg1, arg2, database, trigger):
        allowed_actions = {
            sqlite3.SQLITE_SELECT,
            sqlite3.SQLITE_READ,
            sqlite3.SQLITE_FUNCTION,
        }
        return (
            sqlite3.SQLITE_OK
            if action in allowed_actions
            else sqlite3.SQLITE_DENY
        )

    try:
        connection.set_authorizer(authorize)
        connection.set_progress_handler(
            lambda: 1,  # Replace below with a time-based limit
            0,
        )

        cursor = connection.execute(safe_query)
        columns = [description[0] for description in cursor.description or []]
        rows = cursor.fetchmany(max_rows + 1)

        if len(rows) > max_rows:
            raise ValueError("Query returned too many rows. Please narrow your question.")

        return [dict(zip(columns, tuple(row))) for row in rows]

    except sqlite3.Error as exc:
        raise ValueError("The query could not be executed safely.") from exc
    finally:
        connection.close()
