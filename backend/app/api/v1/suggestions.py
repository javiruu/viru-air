from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.domain.schemas import SuggestionIn
from app.infrastructure.db.models import Suggestion, User
from app.infrastructure.db.session import get_db

router = APIRouter()


@router.post("")
def submit(
    payload: SuggestionIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    s = Suggestion(user_id=current_user.id, text=payload.text, locale=payload.locale)
    db.add(s)
    db.commit()
    return {"status": "received"}
