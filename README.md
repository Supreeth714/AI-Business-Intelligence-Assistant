# AI Business Intelligence Assistant

Ask questions about sales data in plain English and get answers backed by real database queries — no SQL required.

A Groq-hosted LLM translates each question into a SQLite query. The query is validated, executed in a read-only connection, and the **actual result rows** are shown next to a short business-friendly explanation.

---

## Table of Contents

1. [What it does](#what-it-does)
2. [Quick start](#quick-start)
3. [How the data is stored and queried](#how-the-data-is-stored-and-queried)
4. [Architecture](#architecture)
5. [Business rules](#business-rules)
6. [Example questions and expected answers](#example-questions-and-expected-answers)
7. [Safety: preventing destructive or wrong answers](#safety-preventing-destructive-or-wrong-answers)
8. [Project structure](#project-structure)
9. [Configuration](#configuration)
10. [Testing](#testing)
11. [Known limitations](#known-limitations)
12. [Future improvements](#future-improvements)

---

## What it does

- Loads a sales CSV into a local SQLite database.
- Converts natural-language questions into SQL using the database schema (text-to-SQL).
- Validates the SQL before running it and executes it read-only.
- Displays the answer **and** the supporting result table.
- Replies politely when a question cannot be answered from the data (for example, "What are our employee salary costs?").

Supported analysis: total revenue, revenue by product, revenue by region, monthly revenue trend, and month-over-month comparison.

---

## Quick start

**Requirements:** Python 3.10+, a [Groq API key](https://console.groq.com/), and internet access for LLM calls.

```bash
# 1. Get the code
git clone https://github.com/koushiksiripuram/ai-business-intelligence-assistant.git
cd ai-business-intelligence-assistant

# 2. Create a virtual environment
python -m venv venv
source venv/bin/activate        # macOS / Linux
venv\Scripts\activate           # Windows

# 3. Install dependencies
pip install -r requirements.txt

# 4. Add your settings
cp .env.example .env            # Windows: copy .env.example .env
#    then edit .env and set GROQ_API_KEY

# 5. Run
streamlit run app.py
```

In the browser:

1. Click **Load sales data** — imports `data/sample_sales.csv` into SQLite and reports how many records were loaded.
2. Type a question and click **Ask**.
3. Read the answer and check the **Results** table underneath.

---

## How the data is stored and queried

**Storage**

- The CSV is read with Pandas and written to one SQLite table named `sales` (`data/sales.db`).
- Column names are normalised to lowercase `snake_case` (`Unit_price` → `unit_price`).
- `order_date` arrives as `DD-MM-YYYY` and is converted to ISO `YYYY-MM-DD`, so SQLite date functions work. Dates that cannot be parsed become `NULL`.
- Fully blank rows are dropped. A missing `unit_price` is stored as `NULL` — never as `0`.
- Every import replaces the `sales` table, so loading twice does not duplicate rows.

**Querying**

1. The app reads the live schema (table and column names) from SQLite.
2. The schema, the business rules, and the question are sent to the LLM, which returns one `SELECT` statement.
3. The statement is validated (see [Safety](#safety-preventing-destructive-or-wrong-answers)) and executed read-only.
4. The returned rows are passed back to the LLM only to be *worded* as an explanation. Figures come from the database, not from the model.

---

## Architecture

```
User question
     │
     ▼
Streamlit UI (app.py)
     │
     ▼
Schema retrieval ───────── src/database.py
     │
     ▼
LLM text-to-SQL (Groq) ─── src/text_to_sql.py
     │   returns UNSUPPORTED → friendly message
     ▼
SQL validation ─────────── src/sql_validator.py
     │
     ▼
Read-only execution ────── src/query_executor.py  ──►  SQLite (sales table)
     │
     ▼
Response generation ────── src/response_generator.py
     │
     ▼
Answer + supporting results table
```

Each stage is a separate module, so it can be tested or replaced on its own.

---

## Business rules

Revenue is calculated only from eligible transactions:

| Rule | Treatment |
|---|---|
| Status | `Completed` only; `Returned` is excluded |
| Unit price | Rows with missing `unit_price` are excluded (never treated as 0) |
| Quantity | Rows with quantity ≤ 0 are excluded |
| Discount | `discount_amount` is the **total** discount per transaction; missing = 0 |
| Formula | `Revenue = (quantity × unit_price) − COALESCE(discount_amount, 0)` |

These rules are given to the LLM in the prompt. They are **not** enforced in code, so they should be verified (see the checklist below).

In the sample data, 3 of 51 rows are excluded: `TXN0033` (Returned), `TXN0034` (quantity 0) and `TXN0051` (missing price).

---

## Example questions and expected answers

Figures below were calculated independently from `data/sample_sales.csv` and can be used to check the assistant's output.

| Question | Expected result |
|---|---|
| What is the total revenue? | **1,439,200** (48 eligible transactions) |
| Which product generated the highest revenue? | **Monitor — 473,000** (next: Desk 222,500) |
| Which region generated the highest sales? | **South — 411,200** (then North 384,450, East 346,700, West 296,850) |
| What is the monthly revenue trend? | Jan 210,250 · Feb 234,600 · Mar 223,900 · Apr 240,700 · May 318,500 · Jun 211,250 |
| How did revenue change between January and February 2026? | **+24,350 (about +11.6%)** |
| What are our employee salary expenses? | Friendly "outside the dataset" message |

---

## Safety: preventing destructive or wrong answers

Generated SQL is treated as untrusted. Several layers apply:

1. **Prompt rules** — the model is told to use only existing columns, return SQL only, never touch system tables, and return `UNSUPPORTED` for out-of-scope questions. The user's question is treated as data, not instructions.
2. **Pre-check** (`text_to_sql.py`) — rejects empty output, multiple statements, comments, anything not starting with `SELECT`/`WITH`, forbidden keywords (`DROP`, `DELETE`, `PRAGMA`, `ATTACH`, …) and `sqlite_master`-style tables.
3. **Structural validation** (`sql_validator.py`) — parses the query with `sqlglot` and accepts only a single `SELECT`/set-operation. Rejects `INSERT`, `UPDATE`, `DELETE`, `DROP`, `CREATE`, commands, `SELECT … INTO`, and any table outside the allow-list.
4. **Read-only execution** (`query_executor.py`) — the database is opened with SQLite `mode=ro`, and an authorizer permits only `SELECT`, `READ` and function calls.
5. **Result cap** — queries returning more than 500 rows are rejected.
6. **Grounded wording** — the explanation step receives only the query results and is told not to invent figures. If a query returns nothing, the app says so without calling the LLM.

**Unsupported or incorrect answers:** out-of-scope questions return a friendly message; the result table is always displayed so the answer can be checked against the figures.

---

## Project structure

```text
ai-business-intelligence-assistant/
├── app.py                        # Streamlit UI and workflow
├── src/
│   ├── database.py               # CSV import, cleaning, schema lookup
│   ├── text_to_sql.py            # LLM prompt → SQL
│   ├── sql_validator.py          # sqlglot-based validation
│   ├── query_executor.py         # read-only execution
│   ├── response_generator.py     # results → business-friendly answer
│   └── interpreter.py            # reserved (currently empty)
├── tests/
│   ├── test_database.py
│   ├── test_response_generator.py
│   ├── test_analytics.py         # placeholder (empty)
│   ├── test_sql_validator.py     # placeholder (empty)
│   └── README_Tests.md
├── data/
│   ├── sample_sales.csv          # input dataset
│   └── sales.db                  # SQLite database (rebuilt on "Load sales data")
├── requirements.txt
├── .env.example
├── .gitignore
└── README.md
```

---

## Configuration

Set these in `.env` (never commit this file):

| Variable | Purpose | Default |
|---|---|---|
| `GROQ_API_KEY` | Groq API credential (required) | — |
| `GROQ_MODEL` | Model used for SQL and answers | `openai/gpt-oss-120b` |
| `DB_PATH` | SQLite file location | `data/sales.db` |
| `CSV_PATH` | CSV to import | `data/sample_sales.csv` |

**Using your own data:** point `CSV_PATH` at another CSV and click **Load sales data**. The assistant reads the new schema automatically. The business rules currently assume columns named `status`, `quantity`, `unit_price`, `discount_amount` and `order_date`, so a different dataset may need prompt changes in `src/text_to_sql.py`.

---

## Testing

```bash
python -m pytest -q
```

Seven tests currently pass. They cover CSV loading, missing-price preservation, SQLite import, schema inspection and response generation (Groq is mocked, so no API key is needed). See [`tests/README_Tests.md`](tests/README_Tests.md) for the full list, what is *not* yet covered, and a manual verification checklist.

---

## Known limitations

- **No standalone REST API.** The "backend" is a pipeline of Python modules called from the Streamlit app, not an HTTP service.
- **Business rules depend on the LLM.** Generated SQL can be valid but wrong, so revenue rules are not guaranteed to be applied. Check results against the expected figures above.
- **`WITH` (CTE) queries are rejected** by the structural validator, because CTE names are not in the table allow-list. Questions the model answers with a CTE will fail; rephrasing usually works.
- **No query time limit.** The execution progress handler is a placeholder; only the 500-row cap applies.
- **Unit tests do not yet cover SQL safety or revenue calculations.** `test_sql_validator.py` and `test_analytics.py` are empty placeholders.
- **Generated SQL is hidden in the UI** (the "View generated SQL" expander is commented out in `app.py`).
- **Possible duplicate LLM call.** `app.py` calls `generate_sql` twice per question, which doubles latency and API usage.
- **Errors show raw exception text** to the user in some failure paths.
- **Invalid dates** are stored as `NULL` and are not reported to the user.
- Requires internet access and a valid Groq API key.

---

## Future improvements

- Remove the duplicate `generate_sql` call and show the generated SQL in an expander.
- Allow CTE names in the validator.
- Add real query timeouts.
- Fill in the empty test modules (validator, revenue calculations, returned rows, discounts, month comparison).
- Compute core metrics deterministically as a fallback when the LLM's SQL disagrees.
- Add a FastAPI endpoint so the pipeline can be called as an API.
- Report excluded rows ("3 transactions excluded: …") alongside each answer.
- Add CSV upload and charts for trends.
