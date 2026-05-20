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
        "status": {"state": "ok", "message": "Estado reportado por backend"},
        "sections": [
            {
                "title": "Empieza por el panel",
                "body": "Dashboard resume tu estado actual y te deja abrir rapido cada modulo principal.",
                "cta_label": "Ir a Dashboard",
                "cta_href": "/dashboard",
            },
            {
                "title": "Gestiona rutas en Watchlist",
                "body": "Watchlist centraliza rutas vigiladas, estado de precios, refresco y acciones por ruta.",
                "cta_label": "Abrir Watchlist",
                "cta_href": "/watchlist",
            },
            {
                "title": "Busca oportunidades en Quick Search",
                "body": "Quick Search te ayuda a explorar rutas y fechas con filtros y resultados accionables.",
                "cta_label": "Abrir Quick Search",
                "cta_href": "/quick-search",
            },
            {
                "title": "Controla tus alertas",
                "body": "En Alertas puedes activar, pausar y revisar reglas de seguimiento de precio.",
                "cta_label": "Ir a Alertas",
                "cta_href": "/alerts",
            },
            {
                "title": "Revisa recomendaciones",
                "body": "Recomendaciones prioriza oportunidades visibles para decidir con menos ruido.",
                "cta_label": "Ver Recomendaciones",
                "cta_href": "/recomendaciones",
            },
            {
                "title": "Ajusta preferencias",
                "body": "Preferencias concentra busqueda, apariencia, idioma y ajustes de experiencia.",
                "cta_label": "Abrir Preferencias",
                "cta_href": "/preferencias",
            },
            {
                "title": "Soporte directo",
                "body": "Para dudas, incidencias o mejoras, usa contacto, feedback o about us segun contexto.",
                "cta_label": "Ir a Contacto",
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
