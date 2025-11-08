from sqlalchemy import inspect, text

from .database import engine


def ensure_schema():
    """Aggiunge colonne mancanti senza migrazioni complesse."""
    with engine.begin() as connection:
        inspector = inspect(connection)
        if not inspector.has_table("revisioni"):
            return
        columns = {col["name"] for col in inspector.get_columns("revisioni")}
        if "is_released" not in columns:
            connection.execute(
                text("ALTER TABLE revisioni ADD COLUMN is_released BOOLEAN NOT NULL DEFAULT 0")
            )
        if "released_at" not in columns:
            connection.execute(text("ALTER TABLE revisioni ADD COLUMN released_at DATETIME"))
