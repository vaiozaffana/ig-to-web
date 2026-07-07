from alembic.command import stamp
from alembic.config import Config
from sqlalchemy import inspect, text

from app.models.engine import engine

CURRENT_HEAD = "0001_initial_schema"


def main() -> None:
    inspector = inspect(engine)
    table_names = set(inspector.get_table_names())
    has_app_tables = "agent_runs" in table_names or "instagram_posts" in table_names
    has_alembic_version = "alembic_version" in table_names

    if not has_app_tables:
        return

    if not has_alembic_version:
        stamp(Config("alembic.ini"), "head")

    with engine.begin() as connection:
        connection.execute(
            text("CREATE TABLE IF NOT EXISTS alembic_version (version_num VARCHAR(32) NOT NULL)")
        )
        revision = connection.execute(text("SELECT version_num FROM alembic_version")).scalar()
        if not revision:
            connection.execute(text("DELETE FROM alembic_version"))
            connection.execute(
                text("INSERT INTO alembic_version (version_num) VALUES (:revision)"),
                {"revision": CURRENT_HEAD},
            )


if __name__ == "__main__":
    main()
