from sqlalchemy import inspect

from app.database import engine


def get_database_schema() -> str:
    inspector = inspect(engine)

    lines = []

    for table_name in inspector.get_table_names():

        lines.append(f"\nTABLE: {table_name}")

        columns = inspector.get_columns(table_name)

        for column in columns:
            name = column["name"]
            column_type = str(column["type"])

            nullable = "NULL" if column["nullable"] else "NOT NULL"

            lines.append(
                f"  - {name}: {column_type} {nullable}"
            )

        primary_key = inspector.get_pk_constraint(table_name)

        if primary_key["constrained_columns"]:
            lines.append(
                "  PRIMARY KEY: "
                + ", ".join(primary_key["constrained_columns"])
            )

        foreign_keys = inspector.get_foreign_keys(table_name)

        for fk in foreign_keys:
            local_columns = ", ".join(
                fk["constrained_columns"]
            )

            referred_columns = ", ".join(
                fk["referred_columns"]
            )

            lines.append(
                f"  FOREIGN KEY: {local_columns} -> "
                f"{fk['referred_table']}.{referred_columns}"
            )

    return "\n".join(lines)