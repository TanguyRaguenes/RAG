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


def _load_config_or_stop():
    try:
        return load_chat_api_config()
    except RagApiError as error:
        render_api_error(error)
        st.stop()


def _load_my_quota(config, access_token: str | None) -> dict | None:
    with st.spinner("Chargement de ta consommation..."):
        try:
            return get_my_quota_usage(config, access_token)
        except RagApiError as error:
            render_api_error(error)
            return None


def _render_quota_progress(quota: dict) -> None:
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
    st.divider()
    st.subheader("Administration des quotas")
    st.caption(
        "Les utilisateurs humains sont affichés avec leur email. "
        "Les appels machine restent identifiés par leur identifiant pseudonymisé."
    )

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
        active = st.toggle("Quota actif", value=bool(selected_quota["actif"]))
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

    st.toast("Quota mis à jour.")
    st.rerun()


def _quota_to_table_row(quota: dict) -> dict:
    ratio = float(quota["usage_ratio"]) * 100

    return {
        "Utilisateur": _quota_label(quota),
        "Email": quota.get("email") or "-",
        "Actif": "Oui" if quota["actif"] else "Non",
        "Consommés": int(quota["consumed_tokens"]),
        "Max / mois": int(quota["max_tokens_par_mois"]),
        "Utilisation": f"{ratio:.1f}%",
        "Restants": int(quota["remaining_tokens"]),
    }


def _short_user_id(user_id: str) -> str:
    return f"{user_id[:10]}...{user_id[-6:]}"


def _quota_label(quota: dict) -> str:
    return quota.get("email") or f"Compte machine ({_short_user_id(quota['utilisateur_id'])})"


def _quota_by_user_id(quotas: list[dict], user_id: str) -> dict:
    return next(quota for quota in quotas if quota["utilisateur_id"] == user_id)


def _format_tokens(value: int) -> str:
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
