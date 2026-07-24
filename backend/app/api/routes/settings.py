from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_work_settings, require_admin
from app.db.database import get_db
from app.models import User
from app.schemas import WorkSettingsOut, WorkSettingsUpdate

router = APIRouter(prefix="/api", tags=["settings"])


@router.get("/settings", response_model=WorkSettingsOut)
def get_settings(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return get_work_settings(db)


@router.put("/settings", response_model=WorkSettingsOut)
def update_settings(
    payload: WorkSettingsUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(require_admin),
):
    ws = get_work_settings(db)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(ws, field, value)
    db.commit()
    db.refresh(ws)
    return ws
