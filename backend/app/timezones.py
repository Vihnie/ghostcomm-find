from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from sqlalchemy import DateTime
from sqlalchemy.types import TypeDecorator

from app.config import get_settings


def campus_time(value: datetime) -> datetime:
    zone = ZoneInfo(get_settings().app_timezone)
    if value.tzinfo is None:
        return value.replace(tzinfo=zone)
    return value.astimezone(zone)


class UTCDateTime(TypeDecorator):
    # Normalize before storage so databases that drop offsets retain the correct instant.
    impl = DateTime(timezone=True)
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("Database timestamps must include a timezone")
        value = value.astimezone(timezone.utc)
        return value.replace(tzinfo=None) if dialect.name == "sqlite" else value

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)
