import streamlit as st

from app.components.common import (
    load_config_or_stop,
    render_api_error,
    render_page_header,
)
from app.services.auth_service import (
    get_access_token,
    is_usage_admin,
    require_authenticated_user,
)
from app.services.rag_api_client import (
    ChatApiConfig,
    RagApiError,
    get_my_quota_usage,
    list_admin_quota_usages,
    load_chat_api_config,
    update_admin_quota_usage,
)

ADMIN_QUOTA_FLASH_KEY = "admin_quota_flash_message"


def _load_my_quota(
    config: ChatApiConfig,
    access_token: str | None,
) -> dict[str, object] | None:
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


def _render_quota_progress(quota: dict[str, object]) -> None:
    """Affiche la progression de consommation du quota mensuel.

    Args:
        quota: Données de quota utilisateur retournées par l'orchestrator.
    """
    consumed = int(quota["consumed_tokens"])
    maximum = int(quota["max_tokens_par_mois"])
    remaining = int(quota["remaining_tokens"])
    ratio = float(quota["usage_ratio"])
    active = bool(quota["actif"])
    unlimited = bool(quota["illimite"])

    status_label = "Actif" if active else "Désactivé"
    status_method = st.success if active else st.warning
    status_method(f"Quota {status_label.lower()}")

    col_used, col_max, col_remaining = st.columns(3)
    col_used.metric("Consommés", _format_tokens(consumed))
    col_max.metric(
        "Enveloppe mensuelle", "Illimitée" if unlimited else _format_tokens(maximum)
    )
    col_remaining.metric("Restants", "Illimités" if unlimited else _format_tokens(remaining))

    if unlimited:
        st.caption("Aucune limite mensuelle de tokens n'est appliquée.")
    else:
        st.progress(min(max(ratio, 0.0), 1.0))
        st.caption(f"{ratio * 100:.1f}% de l'enveloppe mensuelle utilisée.")

    if not active:
        st.info("Ton accès est désactivé. Rapproche-toi de ton administrateur.")
    elif not unlimited and ratio >= 0.9:
        st.warning("Tu approches de la limite mensuelle.")


def _render_admin_panel(config: ChatApiConfig, access_token: str | None) -> None:
    """Affiche le panneau d'administration des quotas utilisateur.

    Args:
        config: Configuration applicative contenant les URLs, modèles ou paramètres métier nécessaires.
        access_token: Access token OIDC utilisé pour authentifier l'appel HTTP sortant.
    """
    st.divider()
    st.subheader("Administration des quotas")
    st.caption(
        "Les quotas sont rattachés à l'identité Pocket ID stable. "
        "L'email et le nom servent uniquement à l'affichage."
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

    quotas_by_id = {quota["utilisateur_id"]: quota for quota in quotas}
    table_rows = [_quota_to_table_row(quota) for quota in quotas_by_id.values()]
    st.dataframe(table_rows, width="stretch", hide_index=True)

    selected_user_id = st.selectbox(
        "Utilisateur à modifier",
        list(quotas_by_id),
        format_func=lambda user_id: _quota_label(quotas_by_id[user_id]),
    )
    selected_quota = quotas_by_id[selected_user_id]

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
        unlimited = st.checkbox(
            "Tokens illimités",
            value=bool(selected_quota["illimite"]),
            help="Ignore le plafond mensuel tout en continuant à mesurer la consommation.",
        )
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
            unlimited,
        )
    except RagApiError as error:
        render_api_error(error, debug_enabled=True)
        return

    st.session_state[ADMIN_QUOTA_FLASH_KEY] = (
        "Quota mis à jour. Le tableau est actualisé."
    )
    st.rerun()


def _quota_to_table_row(quota: dict[str, object]) -> dict[str, object]:
    """Transforme un quota utilisateur en ligne de tableau administrateur.

    Args:
        quota: Données de quota utilisateur retournées par l'orchestrator.

    Returns:
        Ligne de tableau représentant un quota utilisateur.
    """
    ratio = float(quota["usage_ratio"]) * 100
    unlimited = bool(quota["illimite"])

    return {
        "Utilisateur": _quota_label(quota),
        "Actif": "Oui" if quota["actif"] else "Non",
        "Consommés": int(quota["consumed_tokens"]),
        "Max / mois": "Illimité" if unlimited else int(quota["max_tokens_par_mois"]),
        "Utilisation": "Illimitée" if unlimited else f"{ratio:.1f}%",
        "Restants": "Illimités" if unlimited else int(quota["remaining_tokens"]),
    }


def _short_user_id(user_id: str) -> str:
    """Raccourcit un identifiant utilisateur pour l'affichage en tableau.

    Args:
        user_id: Identifiant interne ou pseudonymisé de l'utilisateur ciblé.

    Returns:
        Identifiant raccourci adapté à l'affichage.
    """
    return f"{user_id[:10]}...{user_id[-6:]}"


def _quota_label(quota: dict[str, object]) -> str:
    """Construit le libellé d'affichage d'un quota utilisateur.

    Args:
        quota: Données de quota utilisateur retournées par l'orchestrator.

    Returns:
        Libellé lisible du quota utilisateur.
    """
    display_name = quota.get("display_name")
    email = quota.get("email")
    preferred_username = quota.get("preferred_username")

    if display_name and email and display_name != email:
        return f"{display_name} ({email})"
    if email:
        return email
    if display_name:
        return display_name
    if preferred_username:
        return preferred_username

    return f"Utilisateur Pocket ID ({_short_user_id(quota['utilisateur_id'])})"


def _format_tokens(value: int) -> str:
    """Formate un nombre de tokens avec séparateurs lisibles.

    Args:
        value: Valeur à convertir, borner ou formater.

    Returns:
        Nombre de tokens formaté pour l'affichage français.
    """
    return f"{value:,}".replace(",", " ")


config = load_config_or_stop(load_chat_api_config)
current_user = require_authenticated_user()
access_token = get_access_token()

render_page_header(
    "Consommation",
    "Suis ton enveloppe mensuelle de tokens et son avancement.",
)

quota = _load_my_quota(config, access_token)
if quota:
    _render_quota_progress(quota)

if is_usage_admin(current_user):
    _render_admin_panel(config, access_token)
