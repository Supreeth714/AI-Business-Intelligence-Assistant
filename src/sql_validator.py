
import sqlglot
from sqlglot import exp


class SQLValidationError(ValueError):
    pass


def validate_sql(query: str, allowed_tables: set[str]) -> str:
    if not query or not query.strip():
        raise SQLValidationError("Please enter a valid question.")

    try:
        statements = sqlglot.parse(query, read="sqlite")
    except sqlglot.errors.ParseError as exc:
        raise SQLValidationError("The generated SQL is invalid.") from exc

    statements = [s for s in statements if s is not None]

    if len(statements) != 1:
        raise SQLValidationError("Only one SQL statement is allowed.")

    tree = statements[0]

    if not isinstance(tree, (exp.Select, exp.Union, exp.Intersect, exp.Except)):
        raise SQLValidationError("Only read-only SELECT queries are allowed.")

    if any(tree.find(node) for node in (
        exp.Insert, exp.Update, exp.Delete, exp.Drop,
        exp.Create, exp.Command, exp.Into,
    )):
        raise SQLValidationError("Unsafe SQL operation detected.")

    allowed = {name.lower() for name in allowed_tables}
    referenced = {table.name.lower() for table in tree.find_all(exp.Table)}

    if not referenced or not referenced.issubset(allowed):
        raise SQLValidationError("Query references an unapproved table.")

    return tree.sql(dialect="sqlite")
