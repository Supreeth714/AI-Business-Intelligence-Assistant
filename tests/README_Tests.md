# Test Guide — AI Business Intelligence Assistant

This document explains what the automated tests cover, how to run them, what is **not** covered yet, and how to check the assistant manually.

---

## Running the tests

From the project root:

```bash
pip install -r requirements.txt
python -m pytest -q
```

Expected output: `7 passed`.

- Tests use temporary CSV files and temporary SQLite databases (`tmp_path`), so your real data is never touched.
- Groq calls are mocked, so **no API key or internet connection is needed**.

---

## Automated tests (7)

### `tests/test_database.py` — data management

| # | Test | Type | What it proves |
|---|---|---|---|
| 1 | `test_load_csv_normalizes_column_names` | Valid | Headers such as `Transaction_Id` and `Unit_price` become `transaction_id` and `unit_price` |
| 2 | `test_missing_price_is_preserved` | Edge case | A blank unit price stays missing (NaN) and is not turned into 0 |
| 3 | `test_missing_csv_raises_error` | Invalid input | A non-existent file raises `FileNotFoundError` |
| 4 | `test_empty_csv_raises_error` | Invalid input | A CSV with headers but no rows raises `ValueError` |
| 5 | `test_import_csv_and_schema` | Valid | Rows are imported into the `sales` table and `get_schema` returns the expected columns |

### `tests/test_response_generator.py` — answer generation

| # | Test | Type | What it proves |
|---|---|---|---|
| 6 | `test_empty_results_do_not_call_groq` | Edge case | An empty result returns "No matching records were found." and makes **no** LLM call |
| 7 | `test_response_uses_actual_results` | Valid | The answer is built from the supplied query rows and the LLM is called exactly once |

### Placeholder files

`tests/test_analytics.py` and `tests/test_sql_validator.py` exist but are **empty**. They are reserved for the tests listed under "Recommended additions" below.

---

## What these tests do not cover

Passing tests show that CSV handling and response generation behave as expected. They do **not** prove that:

- the SQL validator blocks every unsafe query;
- the LLM applies the revenue rules correctly;
- returned, zero-quantity or missing-price transactions are excluded from revenue;
- discounts and month-over-month changes are calculated correctly;
- unsupported questions (for example, employee salaries) are detected.

---

## Manual verification checklist

Until automated tests exist for the items above, run the app (`streamlit run app.py`, click **Load sales data**) and compare against these figures, calculated independently from `data/sample_sales.csv`.

| Question | Expected |
|---|---|
| What is the total revenue? | 1,439,200 |
| Which product generated the highest revenue? | Monitor (473,000) |
| Which region generated the highest sales? | South (411,200) |
| Show the monthly revenue trend | Jan 210,250 · Feb 234,600 · Mar 223,900 · Apr 240,700 · May 318,500 · Jun 211,250 |
| How did revenue change between January and February 2026? | +24,350 (about +11.6%) |
| What are our employee salary expenses? | Friendly "outside the dataset" message, no error |
| (blank question) | Warning asking for a question |

Rows that must be **excluded** from revenue: `TXN0033` (Returned), `TXN0034` (quantity 0), `TXN0051` (missing unit price).

Quick manual safety probes, which should all be rejected by `validate_sql` (`src/sql_validator.py`) when called with `{"sales"}` as the allowed tables:

| Input | Expected rejection |
|---|---|
| `DROP TABLE sales` | Only read-only SELECT queries are allowed |
| `SELECT * FROM sales; DELETE FROM sales` | Only one SQL statement is allowed |
| `SELECT * FROM sqlite_master` | Query references an unapproved table |

---

## Recommended additions

These would turn the empty placeholder files into useful tests:

**`tests/test_sql_validator.py`**
- accepts a simple `SELECT … FROM sales`
- rejects `DROP`, `DELETE`, `UPDATE`, `INSERT`
- rejects multiple statements
- rejects `sqlite_master`
- rejects tables not in the allow-list
- rejects empty input

**`tests/test_analytics.py`** (import the sample CSV into a temporary database, run known SQL, and compare to the expected values)
- total revenue = 1,439,200
- Returned, zero-quantity and missing-price rows are excluded
- discount is subtracted once per transaction
- monthly totals match the table above
- January → February change = +24,350

**Other**
- `execute_query` refuses writes on a read-only connection
- `execute_query` rejects results over 500 rows
- `generate_sql` returns `UNSUPPORTED` for an out-of-scope question (mocked LLM)

---

## Known limitations of the test setup

- LLM output is mocked, so tests do not measure real model accuracy.
- Revenue rules live in the prompt, so they can only be verified end-to-end with real model calls or by testing the SQL separately.
- The validator currently rejects `WITH` (CTE) queries; no test documents this yet.
