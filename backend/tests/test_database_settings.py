import pytest

from app.config import Settings


@pytest.mark.parametrize("scheme", ["postgres", "postgresql", "postgresql+psycopg"])
def test_hosted_postgres_urls_select_the_installed_driver(scheme):
    settings = Settings(
        jwt_secret="x" * 40,
        database_url=f"{scheme}://demo:example@database:5432/campus?sslmode=require",
        _env_file=None,
    )
    assert settings.database_url == (
        "postgresql+psycopg://demo:example@database:5432/campus?sslmode=require"
    )


def test_sqlite_connection_is_unchanged():
    settings = Settings(jwt_secret="x" * 40, database_url="sqlite:///demo.db", _env_file=None)
    assert settings.database_url == "sqlite:///demo.db"
