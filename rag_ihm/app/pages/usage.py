import streamlit as st

from app.components.common import (
    render_api_error,
    render_page_header,
)
from app.services.auth_service import (
    get_access_token,
    is_usage_admin,
    require_authenticated_user,
)
from app.services.rag_api_client import (
    RagApiError,
    get_my_quota_usage,
    list_admin_quota_usages,
    load_chat_api_config,
    update_admin_quota_usage,
)
from app.styles.theme import apply_theme


ADMIN_QUOTA_FLASH_KEY = "admin_quota_flash_message"


def _load_config_or_stop():
    """Charge la configuration requise par une page Streamlit ou arrête le rendu avec un message.

    Returns:
        Configuration de l'API chat nécessaire pour charger les quotas et préférences utilisateur.
    """
    try:
        return load_chat_api_config()
    except RagApiError as error:
        render_api_error(error)
        st.stop()


def _load_my_quota(config, access_token: str | None) -> dict | None:
    """Charge le quota de l'utilisateur connecté pour la page consommation.

    Args:
        config: Configuration applicative contenant les URLs, modèles ou paramètres métier nécessaires.
        access_token: Access token OIDC utilisé pour authentifier l'appel HTTP sortant.

    Returns:
        Données de quota courant ou `None` si le chargement échoue.
    """
    with st.spinner("Chargement de ta consommation..."):
        try:
            return get_my_quota_usage(config, access_token)
        except RagApiError as error:
            render_api_error(error)
            return None


def _render_quota_progress(quota: dict) -> None:
    """Affiche la progression de consommation du quota mensuel.

    Args:
        quota: Données de quota utilisateur retournées par l'orchestrator.
    """
    consumed = int(quota["consumed_tokens"])
    maximum = int(quota["max_tokens_par_mois"])
    remaining = int(quota["remaining_tokens"])
    ratio = float(quota["usage_ratio"])
    active = bool(quota["actif"])

    status_label = "Actif" if active else "Désactivé"
    status_method = st.success if active else st.warning
    status_method(f"Quota {status_label.lower()}")

    col_used, col_max, col_remaining = st.columns(3)
    col_used.metric("Consommés", _format_tokens(consumed))
    col_max.metric("Enveloppe mensuelle", _format_tokens(maximum))
    col_remaining.metric("Restants", _format_tokens(remaining))

    st.progress(min(max(ratio, 0.0), 1.0))
    st.caption(f"{ratio * 100:.1f}% de l'enveloppe mensuelle utilisée.")

    if not active:
        st.info("Ton accès est désactivé. Rapproche-toi de ton administrateur.")
    elif ratio >= 0.9:
        st.warning("Tu approches de la limite mensuelle.")


def _render_admin_panel(config, access_token: str | None) -> None:
    """Affiche le panneau d'administration des quotas utilisateur.

    Args:
        config: Configuration applicative contenant les URLs, modèles ou paramètres métier nécessaires.
        access_token: Access token OIDC utilisé pour authentifier l'appel HTTP sortant.
    """
    st.divider()
    st.subheader("Administration des quotas")
    st.caption(
        "Les utilisateurs avec email sont identifiés par cet email. "
        "Les comptes sans email restent affichés avec un identifiant raccourci."
    )

    flash_message = st.session_state.pop(ADMIN_QUOTA_FLASH_KEY, None)
    if flash_message:
        st.success(flash_message)
        st.toast(flash_message)

    try:
        quotas = list_admin_quota_usages(config, access_token)
    except RagApiError as error:
        render_api_error(error, debug_enabled=True)
        return

    if not quotas:
        st.info("Aucun quota utilisateur à afficher.")
        return

    table_rows = [_quota_to_table_row(quota) for quota in quotas]
    st.dataframe(table_rows, use_container_width=True, hide_index=True)

    selected_user_id = st.selectbox(
        "Utilisateur à modifier",
        [quota["utilisateur_id"] for quota in quotas],
        format_func=lambda user_id: _quota_label(_quota_by_user_id(quotas, user_id)),
    )
    selected_quota = next(
        quota for quota in quotas if quota["utilisateur_id"] == selected_user_id
    )

    with st.form("admin_quota_form"):
        max_tokens = st.number_input(
            "Tokens maximum par mois",
            min_value=1,
            step=1000,
            value=int(selected_quota["max_tokens_par_mois"]),
        )
        active_label = st.radio(
            "Quota",
            ["Actif", "Désactivé"],
            horizontal=True,
            index=0 if bool(selected_quota["actif"]) else 1,
        )
        active = active_label == "Actif"
        submitted = st.form_submit_button("Enregistrer", type="primary")

    if not submitted:
        return

    try:
        update_admin_quota_usage(
            config,
            access_token,
            selected_user_id,
            int(max_tokens),
            active,
        )
    except RagApiError as error:
        render_api_error(error, debug_enabled=True)
        return

    st.session_state[ADMIN_QUOTA_FLASH_KEY] = (
        "Quota mis à jour. Le tableau est actualisé."
    )
    st.rerun()


def _quota_to_table_row(quota: dict) -> dict:
    """Transforme un quota utilisateur en ligne de tableau administrateur.

    Args:
        quota: Données de quota utilisateur retournées par l'orchestrator.

    Returns:
        Ligne de tableau représentant un quota utilisateur.
    """
    ratio = float(quota["usage_ratio"]) * 100

    return {
        "Utilisateur": _quota_label(quota),
        "Actif": "Oui" if quota["actif"] else "Non",
        "Consommés": int(quota["consumed_tokens"]),
        "Max / mois": int(quota["max_tokens_par_mois"]),
        "Utilisation": f"{ratio:.1f}%",
        "Restants": int(quota["remaining_tokens"]),
    }


def _short_user_id(user_id: str) -> str:
    """Raccourcit un identifiant utilisateur pour l'affichage en tableau.

    Args:
        user_id: Identifiant interne ou pseudonymisé de l'utilisateur ciblé.

    Returns:
        Identifiant raccourci adapté à l'affichage.
    """
    return f"{user_id[:10]}...{user_id[-6:]}"


def _quota_label(quota: dict) -> str:
    """Construit le libellé d'affichage d'un quota utilisateur.

    Args:
        quota: Données de quota utilisateur retournées par l'orchestrator.

    Returns:
        Libellé lisible du quota utilisateur.
    """
    return (
        quota.get("email")
        or f"Compte machine ({_short_user_id(quota['utilisateur_id'])})"
    )


def _quota_by_user_id(quotas: list[dict], user_id: str) -> dict:
    """Indexe les quotas par identifiant utilisateur.

    Args:
        quotas: Liste des quotas utilisateur affichés dans le panneau administrateur.
        user_id: Identifiant interne ou pseudonymisé de l'utilisateur ciblé.

    Returns:
        Dictionnaire des quotas indexés par identifiant utilisateur.
    """
    return next(quota for quota in quotas if quota["utilisateur_id"] == user_id)


def _format_tokens(value: int) -> str:
    """Formate un nombre de tokens avec séparateurs lisibles.

    Args:
        value: Valeur à convertir, borner ou formater.

    Returns:
        Nombre de tokens formaté pour l'affichage français.
    """
    return f"{value:,}".replace(",", " ")


config = _load_config_or_stop()
current_user = require_authenticated_user()
access_token = get_access_token()

apply_theme()

render_page_header(
    "Consommation",
    "Suis ton enveloppe mensuelle de tokens et son avancement.",
)

quota = _load_my_quota(config, access_token)
if quota:
    _render_quota_progress(quota)

if is_usage_admin(current_user):
    _render_admin_panel(config, access_token)
