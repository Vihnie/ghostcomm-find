from datetime import datetime, timedelta, timezone

import pytest
from pydantic import ValidationError
from sqlalchemy import text
from sqlalchemy.dialects import mysql, postgresql, sqlite
from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.database import get_engine
from app.models import Item
from app.timezones import UTCDateTime
from tests.conftest import account, report


@pytest.mark.parametrize(
    "submitted",
    [
        "2026-10-19T10:00:00+03:00",
        "2026-10-19T07:00:00Z",
        "2026-10-19T10:00:00",
    ],
)
def test_local_time_round_trip_and_utc_storage(client, submitted):
    owner = account(client)
    item = report(client, owner, occurred_at=submitted)
    assert item["occurred_at"] == "2026-10-19T10:00:00+03:00"
    assert datetime.fromisoformat(item["created_at"]).utcoffset() == timedelta(hours=3)
    fetched = client.get(f"/api/v1/items/{item['id']}", headers=owner).json()
    assert fetched["occurred_at"] == item["occurred_at"]
    with get_engine().connect() as connection:
        stored = connection.scalar(
            text("SELECT occurred_at FROM items WHERE id=:id"), {"id": item["id"]}
        )
        assert datetime.fromisoformat(stored) == datetime(2026, 10, 19, 7)
    with Session(get_engine()) as session:
        assert session.get(Item, item["id"]).occurred_at == datetime(
            2026, 10, 19, 7, tzinfo=timezone.utc
        )


def test_campus_timezone_can_be_changed(client):
    get_settings().app_timezone = "Asia/Kolkata"
    owner = account(client)
    item = report(client, owner, occurred_at="2026-10-19T07:00:00Z")
    assert item["occurred_at"] == "2026-10-19T12:30:00+05:30"


def test_message_timestamps_are_local(client):
    owner, requester = account(client), account(client, "bob")
    item = report(client, owner)
    conversation = client.post(
        "/api/v1/conversations", headers=requester, json={"item_id": item["id"]}
    ).json()
    path = f"/api/v1/conversations/{conversation['id']}/messages"
    response = client.post(path, headers=requester, json={"body": "Is this still available?"})
    assert response.status_code == 201
    assert datetime.fromisoformat(response.json()["created_at"]).utcoffset() == timedelta(hours=3)
    assert client.get(path, headers=owner).json()[0]["created_at"] == response.json()["created_at"]


def test_invalid_timezone_is_rejected():
    with pytest.raises(ValidationError, match="APP_TIMEZONE"):
        Settings(jwt_secret="x" * 40, app_timezone="Invalid/Campus", _env_file=None)


@pytest.mark.parametrize("dialect", [sqlite.dialect(), postgresql.dialect(), mysql.dialect()])
def test_database_adapters_normalize_to_same_instant(dialect):
    column = UTCDateTime()
    source = datetime(2026, 10, 19, 10, tzinfo=timezone(timedelta(hours=3)))
    stored = column.process_bind_param(source, dialect)
    assert stored.hour == 7
    assert column.process_result_value(stored, dialect) == source
    with pytest.raises(ValueError, match="must include a timezone"):
        column.process_bind_param(datetime(2026, 10, 19, 10), dialect)
