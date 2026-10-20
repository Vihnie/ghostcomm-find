from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Response, UploadFile
from fastapi.responses import FileResponse
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import delete, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app import ai, schemas
from app.config import get_settings
from app.database import get_db
from app.media import save_upload
from app.models import Conversation, Item, Match, Media, Message, User
from app.security import (
    current_user,
    dummy_hash,
    issue_token,
    limit_auth,
    limiter,
    passwords,
)

router = APIRouter()
DB = Annotated[Session, Depends(get_db)]
Actor = Annotated[User, Depends(current_user)]
Offset = Annotated[int, Query(ge=0)]
Limit = Annotated[int, Query(ge=1, le=100)]


def get_item(item_id: str, db: Session) -> Item:
    item = db.get(Item, item_id)
    if item is None:
        raise HTTPException(404, "Item not found")
    return item


def owned_item(item_id: str, user: User, db: Session) -> Item:
    item = get_item(item_id, db)
    if item.owner_id != user.id:
        raise HTTPException(403, "Only the report owner can perform this action")
    return item


def get_conversation(conversation_id: str, user: User, db: Session) -> Conversation:
    conversation = db.get(Conversation, conversation_id)
    if conversation is None or user.id not in (conversation.owner_id, conversation.requester_id):
        raise HTTPException(404, "Conversation not found")
    return conversation


def invalidate_matches(item_id: str, db: Session):
    db.execute(delete(Match).where(or_(Match.source_id == item_id, Match.target_id == item_id)))


@router.post(
    "/auth/register",
    response_model=schemas.UserOut,
    status_code=201,
    dependencies=[Depends(limit_auth)],
    tags=["authentication"],
)
def register(body: schemas.Register, db: DB):
    email = str(body.email).lower()
    domains = {
        domain.strip().lower()
        for domain in get_settings().campus_email_domains.split(",")
        if domain.strip()
    }
    if domains and email.rsplit("@", 1)[1] not in domains:
        raise HTTPException(422, "Use an allowed campus email domain")
    user = User(email=email, name=body.name, password_hash=passwords.hash(body.password))
    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "Email is already registered") from None
    db.refresh(user)
    return user


@router.post(
    "/auth/login",
    response_model=schemas.Token,
    dependencies=[Depends(limit_auth)],
    tags=["authentication"],
)
def login(form: Annotated[OAuth2PasswordRequestForm, Depends()], db: DB):
    user = db.scalar(select(User).where(User.email == form.username.strip().lower()))
    if len(form.password) > 128:
        raise HTTPException(401, "Invalid email or password")
    valid = passwords.verify(form.password, user.password_hash if user else dummy_hash)
    if user is None or not valid:
        raise HTTPException(
            401, "Invalid email or password", headers={"WWW-Authenticate": "Bearer"}
        )
    return schemas.Token(access_token=issue_token(user.id))


@router.get("/auth/me", response_model=schemas.UserOut, tags=["authentication"])
def me(user: Actor):
    return user


@router.post("/items", response_model=schemas.ItemOut, status_code=201, tags=["items"])
def create_item(body: schemas.ItemCreate, user: Actor, db: DB):
    limiter.check(f"write:{user.id}", 30)
    item = Item(owner_id=user.id, **body.model_dump())
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


@router.get("/items", response_model=list[schemas.ItemOut], tags=["items"])
def list_items(
    user: Actor,
    db: DB,
    kind: Literal["lost", "found"] | None = None,
    status: Literal["open", "resolved"] | None = "open",
    category: Annotated[str | None, Query(max_length=60)] = None,
    q: Annotated[str | None, Query(min_length=1, max_length=200)] = None,
    mine: bool = False,
    offset: Offset = 0,
    limit: Limit = 20,
):
    statement = select(Item)
    if kind:
        statement = statement.where(Item.kind == kind)
    if status:
        statement = statement.where(Item.status == status)
    if category:
        statement = statement.where(Item.category == category)
    if mine:
        statement = statement.where(Item.owner_id == user.id)
    if q:
        statement = statement.where(
            or_(
                Item.title.icontains(q, autoescape=True),
                Item.description.icontains(q, autoescape=True),
                Item.location.icontains(q, autoescape=True),
            )
        )
    return db.scalars(
        statement.order_by(Item.created_at.desc(), Item.id).offset(offset).limit(limit)
    )


@router.get("/items/{item_id}", response_model=schemas.ItemOut, tags=["items"])
def read_item(item_id: str, user: Actor, db: DB):
    return get_item(item_id, db)


@router.patch("/items/{item_id}", response_model=schemas.ItemOut, tags=["items"])
def update_item(item_id: str, body: schemas.ItemUpdate, user: Actor, db: DB):
    item = owned_item(item_id, user, db)
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(item, field, value)
    invalidate_matches(item_id, db)
    db.commit()
    db.refresh(item)
    return item


@router.delete("/items/{item_id}", status_code=204, tags=["items"])
def delete_item(item_id: str, user: Actor, db: DB):
    item = owned_item(item_id, user, db)
    paths = [
        get_settings().media_dir / record.filename
        for record in db.scalars(select(Media).where(Media.item_id == item_id))
    ]
    db.delete(item)
    db.commit()
    for path in paths:
        path.unlink(missing_ok=True)
    return Response(status_code=204)


@router.post(
    "/items/{item_id}/media", response_model=schemas.MediaOut, status_code=201, tags=["media"]
)
def upload_media(item_id: str, file: UploadFile, user: Actor, db: DB):
    limiter.check(f"upload:{user.id}", 10)
    item = owned_item(item_id, user, db)
    invalidate_matches(item_id, db)
    return save_upload(file, item, db)


@router.get("/items/{item_id}/media", response_model=list[schemas.MediaOut], tags=["media"])
def list_media(item_id: str, user: Actor, db: DB):
    get_item(item_id, db)
    return db.scalars(select(Media).where(Media.item_id == item_id).order_by(Media.id))


@router.get("/media/{media_id}", tags=["media"])
def download_media(media_id: str, user: Actor, db: DB):
    record = db.get(Media, media_id)
    if record is None:
        raise HTTPException(404, "Media not found")
    path = get_settings().media_dir / record.filename
    if not path.is_file():
        raise HTTPException(404, "Media file not found")
    return FileResponse(path, media_type=record.content_type, filename=record.filename)


@router.delete("/media/{media_id}", status_code=204, tags=["media"])
def delete_media(media_id: str, user: Actor, db: DB):
    record = db.get(Media, media_id)
    if record is None:
        raise HTTPException(404, "Media not found")
    owned_item(record.item_id, user, db)
    invalidate_matches(record.item_id, db)
    path = get_settings().media_dir / record.filename
    db.delete(record)
    db.commit()
    path.unlink(missing_ok=True)
    return Response(status_code=204)


@router.post("/search/ai", response_model=list[schemas.MatchOut], tags=["AI matching"])
def search_ai(body: schemas.AISearch, user: Actor, db: DB):
    limiter.check(f"ai:{user.id}", 5)
    statement = select(Item).where(Item.kind == body.kind, Item.status == "open")
    if body.category:
        statement = statement.where(Item.category == body.category)
    candidates = list(db.scalars(statement.order_by(Item.created_at.desc()).limit(100)))
    return ai.find_matches(body.description, candidates, db)


@router.post(
    "/items/{item_id}/matches", response_model=list[schemas.MatchOut], tags=["AI matching"]
)
def generate_matches(item_id: str, user: Actor, db: DB):
    limiter.check(f"ai:{user.id}", 5)
    item = owned_item(item_id, user, db)
    if item.status != "open":
        raise HTTPException(409, "Reopen the report before requesting matches")
    candidates = list(
        db.scalars(
            select(Item)
            .where(
                Item.kind != item.kind,
                Item.status == "open",
                Item.owner_id != user.id,
            )
            .order_by(Item.created_at.desc())
            .limit(100)
        )
    )
    hits = ai.find_matches(f"{item.title} {item.description} {item.category}", candidates, db, item)
    db.execute(delete(Match).where(Match.source_id == item_id))
    for hit in hits:
        db.add(Match(source_id=item_id, **hit.model_dump()))
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "Report changed during matching; retry the request") from None
    return hits


@router.get("/items/{item_id}/matches", response_model=list[schemas.MatchOut], tags=["AI matching"])
def list_matches(item_id: str, user: Actor, db: DB):
    owned_item(item_id, user, db)
    return db.scalars(
        select(Match)
        .join(Item, Match.target_id == Item.id)
        .where(
            Match.source_id == item_id,
            Item.status == "open",
        )
        .order_by(Match.score.desc())
    )


@router.post(
    "/conversations",
    response_model=schemas.ConversationOut,
    status_code=201,
    tags=["communication"],
)
def start_conversation(body: schemas.ConversationCreate, user: Actor, db: DB):
    limiter.check(f"write:{user.id}", 30)
    item = get_item(body.item_id, db)
    if item.owner_id == user.id:
        raise HTTPException(422, "You cannot contact yourself")
    if item.status != "open":
        raise HTTPException(409, "This report is resolved")
    statement = select(Conversation).where(
        Conversation.item_id == item.id, Conversation.requester_id == user.id
    )
    existing = db.scalar(statement)
    if existing:
        return existing
    conversation = Conversation(item_id=item.id, requester_id=user.id, owner_id=item.owner_id)
    db.add(conversation)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        existing = db.scalar(statement)
        if existing:
            return existing
        raise HTTPException(409, "Report changed; retry the request") from None
    db.refresh(conversation)
    return conversation


@router.get("/conversations", response_model=list[schemas.ConversationOut], tags=["communication"])
def list_conversations(user: Actor, db: DB, offset: Offset = 0, limit: Limit = 20):
    return db.scalars(
        select(Conversation)
        .where(
            or_(
                Conversation.owner_id == user.id,
                Conversation.requester_id == user.id,
            )
        )
        .order_by(Conversation.id)
        .offset(offset)
        .limit(limit)
    )


@router.post(
    "/conversations/{conversation_id}/messages",
    response_model=schemas.MessageOut,
    status_code=201,
    tags=["communication"],
)
def send_message(conversation_id: str, body: schemas.MessageCreate, user: Actor, db: DB):
    limiter.check(f"message:{user.id}", 30)
    get_conversation(conversation_id, user, db)
    message = Message(conversation_id=conversation_id, sender_id=user.id, body=body.body)
    db.add(message)
    db.commit()
    db.refresh(message)
    return message


@router.get(
    "/conversations/{conversation_id}/messages",
    response_model=list[schemas.MessageOut],
    tags=["communication"],
)
def list_messages(conversation_id: str, user: Actor, db: DB, offset: Offset = 0, limit: Limit = 50):
    get_conversation(conversation_id, user, db)
    return db.scalars(
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .order_by(Message.created_at, Message.id)
        .offset(offset)
        .limit(limit)
    )
