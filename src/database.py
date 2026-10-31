
import re
import sqlite3
from pathlib import Path

import pandas as pd


def normalize_column_name(name: str, index: int) -> str:
    """Convert column names into safe, consistent identifiers."""
    name = name.strip().lower()
    name = re.sub(r"[^a-z0-9]+", "_", name).strip("_")
    return name or f"column_{index}"


def get_connection(db_path: str | Path) -> sqlite3.Connection:
    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    return connection


def load_csv(csv_path: str | Path) -> pd.DataFrame:
    """Load a CSV without assuming specific business columns."""
    path = Path(csv_path)

    if not path.is_file():
        raise FileNotFoundError(f"CSV file not found: {path}")

    df = pd.read_csv(path)

    if df.empty:
        raise ValueError("The CSV contains no records.")

    df.columns = [
        normalize_column_name(str(column), index)
        for index, column in enumerate(df.columns, start=1)
    ]

    if len(set(df.columns)) != len(df.columns):
        raise ValueError(
            "Column names are duplicated after normalization. "
            "Please rename the conflicting columns in the CSV."
        )

    df = df.dropna(how="all").copy()
    
    if "order_date" in df.columns:
        parsed_dates = pd.to_datetime(
            df["order_date"],
            format="%d-%m-%Y",
            errors="coerce",
        )
        df["order_date"] = parsed_dates.dt.strftime("%Y-%m-%d")

    if df.empty:
        raise ValueError("The CSV contains no usable records.")

    return df


def import_csv(
    csv_path: str | Path,
    db_path: str | Path,
    replace: bool = True,
) -> int:
    """Import CSV data into the sales table."""
    df = load_csv(csv_path)

    with get_connection(db_path) as connection:
        df.to_sql(
            "sales",
            connection,
            if_exists="replace" if replace else "append",
            index=False,
        )

    return len(df)


def get_schema(db_path: str | Path) -> dict[str, list[str]]:
    """Retrieve the current database tables and their columns."""
    with get_connection(db_path) as connection:
        tables = connection.execute("""
            SELECT name
            FROM sqlite_master
            WHERE type = 'table'
              AND name NOT LIKE 'sqlite_%'
            ORDER BY name
        """).fetchall()

        schema = {}

        for table in tables:
            table_name = table["name"]
            columns = connection.execute(
                f'PRAGMA table_info("{table_name}")'
            ).fetchall()

            schema[table_name] = [
                column["name"] for column in columns
            ]

    return schema
