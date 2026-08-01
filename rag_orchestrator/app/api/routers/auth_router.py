from fastapi import APIRouter, Depends

from app.api.dependencies import get_current_user
from app.schemas.authenticated_user_schema import AuthenticatedUser

router = APIRouter(prefix="/auth", tags=["auth"])
current_user_dependency = Depends(get_current_user)


@router.get("/me", response_model=AuthenticatedUser)
async def get_me(
    current_user: AuthenticatedUser = current_user_dependency,
) -> AuthenticatedUser:
    """Retourne les informations de l'utilisateur authentifié courant.

    Args:
        current_user: Utilisateur authentifié issu du token OIDC courant.

    Returns:
        Profil minimal de l'utilisateur courant avec groupes et e-mail éventuel.
    """
    return current_user
