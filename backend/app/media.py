import io
import warnings
from uuid import uuid4

import filetype
from fastapi import HTTPException, UploadFile
from PIL import Image, UnidentifiedImageError
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import Item, Media

IMAGE_TYPES = {"image/jpeg": "jpg", "image/png": "png", "image/webp": "webp"}
VIDEO_TYPES = {"video/mp4": "mp4", "video/webm": "webm"}
Image.MAX_IMAGE_PIXELS = 20_000_000


def save_upload(upload: UploadFile, item: Item, db: Session) -> Media:
    settings = get_settings()
    count = db.scalar(select(func.count()).select_from(Media).where(Media.item_id == item.id))
    if count >= 5:
        raise HTTPException(409, "An item can have at most five media files")
    try:
        data = upload.file.read(settings.max_upload_bytes + 1)
    finally:
        upload.file.close()
    if len(data) > settings.max_upload_bytes:
        raise HTTPException(413, "File exceeds upload limit")
    detected = filetype.guess(data)
    allowed = IMAGE_TYPES | VIDEO_TYPES
    if detected is None or detected.mime not in allowed:
        raise HTTPException(415, "Supported media: JPEG, PNG, WebP, MP4, WebM")
    mime = detected.mime
    if mime in IMAGE_TYPES:
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("error", Image.DecompressionBombWarning)
                with Image.open(io.BytesIO(data)) as source:
                    source.load()
                    # Re-encoding removes metadata and appended content from images.
                    clean = io.BytesIO()
                    source.convert("RGB").save(clean, format="JPEG", quality=90)
                    data = clean.getvalue()
                    mime = "image/jpeg"
        except (
            UnidentifiedImageError,
            OSError,
            ValueError,
            Image.DecompressionBombError,
            Image.DecompressionBombWarning,
        ):
            raise HTTPException(415, "Invalid or oversized image") from None
    if len(data) > settings.max_upload_bytes:
        raise HTTPException(413, "Processed file exceeds upload limit")
    filename = f"{uuid4()}.{allowed[mime]}"
    path = settings.media_dir / filename
    path.write_bytes(data)
    record = Media(item_id=item.id, filename=filename, content_type=mime, size=len(data))
    try:
        db.add(record)
        db.commit()
        db.refresh(record)
    except Exception:
        db.rollback()
        path.unlink(missing_ok=True)
        raise
    return record
