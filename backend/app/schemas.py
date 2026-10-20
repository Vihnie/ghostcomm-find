from datetime import datetime
from typing import Annotated, Literal

from pydantic import (
    AfterValidator,
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
    StringConstraints,
    field_validator,
)

from app.timezones import campus_time

CampusDatetime = Annotated[datetime, AfterValidator(campus_time)]


class Input(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")


class Output(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class Register(Input):
    email: EmailStr
    name: str = Field(min_length=1, max_length=100)
    password: Annotated[
        str, StringConstraints(strip_whitespace=False, min_length=12, max_length=128)
    ]


class UserOut(Output):
    id: str
    email: str
    name: str


class Token(Output):
    access_token: str
    token_type: str = "bearer"


class ItemCreate(Input):
    kind: Literal["lost", "found"]
    title: str = Field(min_length=3, max_length=150)
    description: str = Field(min_length=10, max_length=5000)
    category: str = Field(min_length=1, max_length=60)
    location: str = Field(min_length=1, max_length=200)
    occurred_at: CampusDatetime


class ItemUpdate(Input):
    title: str | None = Field(default=None, min_length=3, max_length=150)
    description: str | None = Field(default=None, min_length=10, max_length=5000)
    category: str | None = Field(default=None, min_length=1, max_length=60)
    location: str | None = Field(default=None, min_length=1, max_length=200)
    occurred_at: CampusDatetime | None = None
    status: Literal["open", "resolved"] | None = None

    @field_validator("title", "description", "category", "location", "occurred_at", "status")
    @classmethod
    def reject_explicit_null(cls, value):
        if value is None:
            raise ValueError("Field cannot be null")
        return value


class ItemOut(Output):
    id: str
    owner_id: str
    kind: str
    title: str
    description: str
    category: str
    location: str
    occurred_at: CampusDatetime
    status: str
    created_at: CampusDatetime


class MediaOut(Output):
    id: str
    item_id: str
    content_type: str
    size: int


class MatchOut(Output):
    target_id: str
    score: float
    reason: str


class AISearch(Input):
    description: str = Field(min_length=10, max_length=5000)
    kind: Literal["lost", "found"] = "found"
    category: str | None = Field(default=None, min_length=1, max_length=60)


class AIHit(Input):
    target_id: str
    score: float = Field(ge=0, le=1, allow_inf_nan=False)
    reason: str = Field(min_length=1, max_length=1000)


class AIResult(Input):
    matches: list[AIHit] = Field(max_length=8)


class ConversationCreate(Input):
    item_id: str


class ConversationOut(Output):
    id: str
    item_id: str
    requester_id: str
    owner_id: str


class MessageCreate(Input):
    body: str = Field(min_length=1, max_length=4000)


class MessageOut(Output):
    id: str
    conversation_id: str
    sender_id: str
    body: str
    created_at: CampusDatetime
