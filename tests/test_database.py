
import pandas as pd
import pytest

from src.database import get_schema, import_csv, load_csv


def write_csv(path, content):
    path.write_text(content, encoding="utf-8")
    return path


def test_load_csv_normalizes_column_names(tmp_path):
    csv_path = write_csv(
        tmp_path / "sales.csv",
        "Transaction_Id,Product,Quantity,Unit_price\n"
        "TXN0001,Laptop Stand,10,1200\n",
    )

    df = load_csv(csv_path)

    assert "transaction_id" in df.columns
    assert "unit_price" in df.columns
    assert len(df) == 1


def test_missing_price_is_preserved(tmp_path):
    csv_path = write_csv(
        tmp_path / "sales.csv",
        "Transaction_Id,Product,Quantity,Unit_price\n"
        "TXN0001,Laptop Stand,10,1200\n"
        "TXN0002,Laptop Stand,5,\n",
    )

    df = load_csv(csv_path)

    assert len(df) == 2
    assert pd.isna(df.loc[1, "unit_price"])


def test_missing_csv_raises_error(tmp_path):
    with pytest.raises(FileNotFoundError):
        load_csv(tmp_path / "missing.csv")


def test_empty_csv_raises_error(tmp_path):
    csv_path = write_csv(
        tmp_path / "empty.csv",
        "Transaction_Id,Product\n",
    )

    with pytest.raises(ValueError):
        load_csv(csv_path)


def test_import_csv_and_schema(tmp_path):
    csv_path = write_csv(
        tmp_path / "sales.csv",
        "Transaction_Id,Product,Quantity,Unit_price\n"
        "TXN0001,Laptop Stand,10,1200\n"
        "TXN0002,Monitor,2,9500\n",
    )
    db_path = tmp_path / "db" / "sales.db"

    count = import_csv(csv_path, db_path)
    schema = get_schema(db_path)

    assert count == 2
    assert "sales" in schema
    assert {
        "transaction_id",
        "product",
        "quantity",
        "unit_price",
    }.issubset(set(schema["sales"]))
