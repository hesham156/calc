from sqlalchemy.orm import Session

from app.models import WorkSettings


def get_work_settings(db: Session) -> WorkSettings:
    from app.services.calculator import get_or_create_settings

    return get_or_create_settings(db)
