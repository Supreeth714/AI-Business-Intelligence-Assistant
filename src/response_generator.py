
import json
import os

from groq import Groq


def generate_response(question: str, sql: str, results: list[dict]) -> dict:
    """Generate a business-friendly answer based on actual SQL results."""

    if not results:
        answer = "No matching records were found."
    else:
        client = Groq()

        response = client.chat.completions.create(
            model=os.getenv("GROQ_MODEL", "openai/gpt-oss-120b"),
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a business intelligence assistant. "
                        "Answer the user's question clearly and concisely "
                        "using only the supplied SQL results. "
                        "Do not invent or recalculate unsupported figures. "
                        "For trends, describe changes across periods. "
                        "For comparisons, include absolute and percentage "
                        "changes only when supported by the results. "
                        "If the results do not answer the question, say so."
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        f"Question: {question}\n"
                        f"Query results: {json.dumps(results, default=str)}"
                    ),
                },
            ],
            temperature=0,
        )

        answer = response.choices[0].message.content.strip()

    return {
        "question": question,
        "answer": answer,
        "results": results,
    }
