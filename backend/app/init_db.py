from pathlib import Path

from sqlalchemy.engine import make_url

from app import models  # noqa: F401
from app.config import get_settings
from app.database import Base, get_engine


def main():
    settings = get_settings()
    url = make_url(settings.database_url)
    if url.drivername.startswith("sqlite") and url.database and url.database != ":memory:":
        Path(url.database).parent.mkdir(parents=True, exist_ok=True)
    settings.media_dir.mkdir(parents=True, exist_ok=True)
    Base.metadata.create_all(get_engine())
    print("Database initialized")


if __name__ == "__main__":
    main()
