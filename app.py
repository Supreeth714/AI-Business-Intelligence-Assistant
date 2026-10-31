
import os
import streamlit as st
from dotenv import load_dotenv

from src.database import get_schema, import_csv
from src.text_to_sql import generate_sql
from src.sql_validator import validate_sql
from src.query_executor import execute_query
from src.response_generator import generate_response

load_dotenv()

DB_PATH = os.getenv("DB_PATH", "data/sales.db")
CSV_PATH = os.getenv("CSV_PATH", "data/sample_sales.csv")

st.set_page_config(page_title="AI Business Intelligence", page_icon="📊")
st.title("AI Business Intelligence Assistant")
st.write("Ask questions about your sales data in natural language.")

if "db_ready" not in st.session_state:
    st.session_state.db_ready = False

if st.button("Load sales data"):
    try:
        count = import_csv(CSV_PATH, DB_PATH)
        st.session_state.db_ready = True
        st.success(f"Loaded {count} valid records.")
    except Exception as exc:
        st.error(f"Could not load sales data: {exc}")

question = st.text_area(
    "Your business question",
    placeholder="Example: Which product generated the highest revenue?",
)

if st.button("Ask", type="primary"):
    if not question.strip():
        st.warning("Please enter a question.")
    elif not os.getenv("GROQ_API_KEY"):
        st.error("Configure GROQ_API_KEY in your .env file.")
    else:
        try:
            schema = get_schema(DB_PATH)
            if "sales" not in schema:
                st.error("Load the sales CSV first.")
            else:
                with st.spinner("Analyzing your question..."):
                    sql = generate_sql(question, schema)
                    sql = generate_sql(question, schema)

                    if sql == "UNSUPPORTED":
                        st.info(
                            "I can help with questions about your sales data, "
                            "such as revenue, products, regions, and monthly trends."
                        )
                        st.caption(
                            "Try: What was the total revenue? "
                            "Which product sold the most? "
                            "Show monthly revenue."
                        )
                        st.stop()
                    validate_sql(sql, set(schema.keys()))
                    results = execute_query(DB_PATH, sql, set(schema.keys()))
                    response = generate_response(question, sql, results)

                st.subheader("Answer")
                st.write(response["answer"])

                st.subheader("Results")
                if results:
                    st.dataframe(results, use_container_width=True)
                else:
                    st.info("No matching records.")

                # with st.expander("View generated SQL"):
                #     st.code(sql, language="sql")

        except Exception as exc:
            st.error(f"{type(exc).__name__}: {exc}")
