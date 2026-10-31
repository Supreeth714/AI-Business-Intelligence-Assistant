
from types import SimpleNamespace
from unittest.mock import MagicMock

import src.response_generator as response_generator


def test_empty_results_do_not_call_groq(monkeypatch):
    groq_mock = MagicMock()
    monkeypatch.setattr(response_generator, "Groq", groq_mock)

    result = response_generator.generate_response(
        "What is total revenue?", "SELECT 1", []
    )

    assert result["answer"] == "No matching records were found."
    assert result["results"] == []
    assert "sql" not in result
    groq_mock.assert_not_called()


def test_response_uses_actual_results(monkeypatch):
    completion = SimpleNamespace(
        choices=[
            SimpleNamespace(
                message=SimpleNamespace(
                    content="Laptop Stand revenue is 96000."
                )
            )
        ]
    )

    client = MagicMock()
    client.chat.completions.create.return_value = completion

    groq_mock = MagicMock(return_value=client)
    monkeypatch.setattr(response_generator, "Groq", groq_mock)

    rows = [{"product": "Laptop Stand", "revenue": 96000}]

    result = response_generator.generate_response(
        "What is Laptop Stand revenue?", "SELECT ...", rows
    )

    assert result["answer"] == "Laptop Stand revenue is 96000."
    assert result["results"] == rows
    assert "sql" not in result
    client.chat.completions.create.assert_called_once()
