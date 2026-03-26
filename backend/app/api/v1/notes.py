from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.domain.schemas import NoteIn, NoteOut, NoteUpdateIn
from app.infrastructure.db.models import User, UserNote
from app.infrastructure.db.session import get_db

router = APIRouter()


@router.get("", response_model=list[NoteOut])
def list_notes(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[NoteOut]:
    notes = db.scalars(
        select(UserNote)
        .where(UserNote.user_id == current_user.id)
        .order_by(UserNote.updated_at.desc())
    ).all()
    return [
        NoteOut(
            id=note.id,
            title=note.title,
            body=note.body,
            created_at=note.created_at,
            updated_at=note.updated_at,
        )
        for note in notes
    ]


@router.post("", response_model=NoteOut)
def create_note(
    payload: NoteIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> NoteOut:
    note = UserNote(
        user_id=current_user.id,
        title=payload.title.strip(),
        body=payload.body.strip(),
    )
    db.add(note)
    db.commit()
    db.refresh(note)
    return NoteOut(
        id=note.id,
        title=note.title,
        body=note.body,
        created_at=note.created_at,
        updated_at=note.updated_at,
    )


@router.put("/{note_id}", response_model=NoteOut)
def update_note(
    note_id: str,
    payload: NoteUpdateIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> NoteOut:
    note = db.scalar(
        select(UserNote).where(UserNote.id == note_id, UserNote.user_id == current_user.id)
    )
    if not note:
        raise HTTPException(status_code=404, detail="note_not_found")

    if payload.title is not None:
        note.title = payload.title.strip()
    if payload.body is not None:
        note.body = payload.body.strip()

    db.commit()
    db.refresh(note)
    return NoteOut(
        id=note.id,
        title=note.title,
        body=note.body,
        created_at=note.created_at,
        updated_at=note.updated_at,
    )


@router.delete("/{note_id}")
def delete_note(
    note_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    note = db.scalar(
        select(UserNote).where(UserNote.id == note_id, UserNote.user_id == current_user.id)
    )
    if not note:
        raise HTTPException(status_code=404, detail="note_not_found")
    db.delete(note)
    db.commit()
    return {"status": "ok"}
