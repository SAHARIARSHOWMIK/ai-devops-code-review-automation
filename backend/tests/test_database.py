from sqlalchemy import text

from app.core.database import build_engine


def test_in_memory_sqlite_uses_shared_connection_pool():
    engine = build_engine("sqlite:///:memory:")
    with engine.begin() as connection:
        connection.execute(text("CREATE TABLE sample (value INTEGER NOT NULL)"))
        connection.execute(text("INSERT INTO sample (value) VALUES (42)"))

    try:
        with engine.connect() as connection:
            assert (
                connection.execute(text("SELECT value FROM sample")).scalar_one() == 42
            )
    finally:
        engine.dispose()
