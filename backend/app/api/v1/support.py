from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.domain.schemas import FeedbackIn
from app.infrastructure.db.models import SupportFeedback, User
from app.infrastructure.db.session import get_db

router = APIRouter()


def help_payload() -> dict:
    return {
        "title": "Centro de ayuda",
        "status": {
            "state": "ok",
            "message": "Empieza por un flujo principal y deja soporte o ajustes para cuando de verdad lo necesites.",
        },
        "sections": [
            {
                "title": "Empieza por el panel",
                "body": "Dashboard resume tu estado actual y te orienta hacia el siguiente paso con menos ruido.",
                "cta_label": "Ir a Dashboard",
                "cta_href": "/dashboard",
            },
            {
                "title": "Busca oportunidades en Quick Search",
                "body": "Quick Search es el mejor punto de entrada cuando todavia estas explorando rutas y fechas.",
                "cta_label": "Abrir Quick Search",
                "cta_href": "/quick-search",
            },
            {
                "title": "Gestiona rutas en Watchlist",
                "body": "Watchlist tiene sentido cuando ya sabes que rutas quieres vigilar y revisar con frecuencia.",
                "cta_label": "Abrir Watchlist",
                "cta_href": "/watchlist",
            },
            {
                "title": "Controla tus alertas",
                "body": "Alertas te sirve para guardar una regla y volver despues; no hace falta abrirlo antes de tener una ruta clara.",
                "cta_label": "Ir a Alertas",
                "cta_href": "/alerts",
            },
            {
                "title": "Revisa recomendaciones",
                "body": "Recomendaciones te da contexto extra cuando quieres comparar opciones sin perder el foco principal.",
                "cta_label": "Ver Recomendaciones",
                "cta_href": "/recomendaciones",
            },
            {
                "title": "Ajusta preferencias",
                "body": "Preferencias reune idioma, apariencia y ajustes personales, pero no es el primer paso del flujo.",
                "cta_label": "Abrir Preferencias",
                "cta_href": "/preferencias",
            },
            {
                "title": "Soporte directo",
                "body": "Usa contacto o feedback solo cuando necesites ayuda concreta, incidencias o compartir una mejora.",
                "cta_label": "Abrir contacto de soporte",
                "cta_href": "/soporte/contacto",
            },
        ],
    }


@router.get("/help")
def get_help(current_user: User = Depends(get_current_user)) -> dict:
    _ = current_user
    return help_payload()


@router.post("/feedback")
def submit_feedback(
    payload: FeedbackIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    db.add(
        SupportFeedback(
            user_id=current_user.id,
            feedback_type=payload.feedback_type,
            message=payload.message,
            attachment_url=payload.attachment_url,
        )
    )
    db.commit()
    return {"status": "ok"}
