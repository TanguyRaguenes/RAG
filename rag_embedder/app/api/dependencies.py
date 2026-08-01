from fastapi import Request

from app.core.config import EmbedderConfig


def get_config(request: Request) -> EmbedderConfig:
    """Retourne la configuration chargée au démarrage de l'application FastAPI.

    Args:
        request: Requête HTTP FastAPI en cours de traitement.

    Returns:
        Configuration applicative disponible dans `app.state`.
    """
    return request.app.state.config
