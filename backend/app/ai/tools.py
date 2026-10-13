from decimal import Decimal
from datetime import date, datetime

from sqlalchemy import text

from app.database import engine


def make_json_safe(value):
    if isinstance(value, Decimal):
        return float(value)

    if isinstance(value, (datetime, date)):
        return value.isoformat()

    return value


def execute_readonly_sql(sql: str):

    sql_clean = sql.strip().lower()
    sql_clean = sql_clean.rstrip(";").strip()

    if not (
        sql_clean.startswith("select")
        or sql_clean.startswith("with")
    ):
        raise ValueError(
            "Only SELECT and WITH queries are allowed."
        )

    forbidden = [
        "insert ",
        "update ",
        "delete ",
        "drop ",
        "alter ",
        "truncate ",
        "create ",
        "replace ",
        "grant ",
        "revoke ",
    ]

    for keyword in forbidden:
        if keyword in sql_clean:
            raise ValueError(
                f"Forbidden SQL operation: {keyword.strip()}"
            )

    with engine.connect() as connection:

        result = connection.execute(text(sql))

        columns = list(result.keys())

        rows = []

        for row in result.fetchall():

            row_data = {}

            for column, value in zip(columns, row):

                row_data[column] = make_json_safe(value)

            rows.append(row_data)

        return rows