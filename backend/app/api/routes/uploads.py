import uuid
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.config import settings
from app.db.database import get_db
from app.models import Upload, User
from app.schemas import UploadOut
from app.services.ingest import process_upload
from app.services.parser.engine import ALLOWED_EXTENSIONS

router = APIRouter(prefix="/api", tags=["uploads"])


@router.post("/upload", response_model=UploadOut, status_code=201)
async def upload_file(
    background: BackgroundTasks,
    file: UploadFile,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    ext = Path(file.filename or "").suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(400, f"Unsupported file type '{ext}'. Allowed: CSV, XLS, XLSX")

    content = await file.read()
    if len(content) == 0:
        raise HTTPException(400, "File is empty")
    if len(content) > settings.MAX_UPLOAD_MB * 1024 * 1024:
        raise HTTPException(413, f"File exceeds {settings.MAX_UPLOAD_MB} MB limit")

    stored_name = f"{uuid.uuid4().hex}{ext}"
    dest = Path(settings.UPLOAD_DIR) / stored_name
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(content)

    upload = Upload(filename=file.filename or stored_name, stored_name=stored_name)
    db.add(upload)
    db.commit()
    db.refresh(upload)

    background.add_task(process_upload, upload.id)
    return upload


@router.get("/uploads", response_model=list[UploadOut])
def list_uploads(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return db.scalars(select(Upload).order_by(Upload.id.desc()).limit(50)).all()


@router.get("/uploads/{upload_id}", response_model=UploadOut)
def get_upload(upload_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    upload = db.get(Upload, upload_id)
    if upload is None:
        raise HTTPException(404, "Upload not found")
    return upload
