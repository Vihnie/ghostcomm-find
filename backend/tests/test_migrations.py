from alembic import command
from alembic.config import Config
from sqlalchemy import inspect

from app.database import get_engine


def test_migrations_round_trip(client):
    # The fixture creates a temporary database; only that database is modified here.
    from app.database import Base

    Base.metadata.drop_all(get_engine())
    config = Config("alembic.ini")
    command.upgrade(config, "head")
    assert "messages" in inspect(get_engine()).get_table_names()
    command.check(config)
    command.downgrade(config, "base")
    assert "users" not in inspect(get_engine()).get_table_names()
    command.upgrade(config, "head")
    assert "users" in inspect(get_engine()).get_table_names()
