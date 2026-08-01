from typing import Any

import streamlit as st

from app.components.common import render_sidebar_header
from app.core.logging import configure_json_logging
from app.services.auth_service import (
    handle_oidc_callback,
    is_usage_admin,
    logout,
    require_authenticated_user,
)

configure_json_logging("rag_ihm")

st.set_page_config(
    page_title="IsiDore",
)

handle_oidc_callback()


def _render_global_sidebar(current_user: dict[str, Any] | None) -> None:
    """Affiche l'identité de l'utilisateur et l'action de déconnexion."""
    with st.sidebar:
        render_sidebar_header(current_user)
        st.divider()

        if st.button("Se déconnecter", width="stretch"):
            logout()
            st.rerun()


current_user = require_authenticated_user()
_render_global_sidebar(current_user)

pages = [
    st.Page("pages/chat.py", title="Discussion", default=True),
    st.Page("pages/usage.py", title="Consommation"),
]

if is_usage_admin(current_user):
    pages.append(st.Page("pages/feedbacks.py", title="Avis"))
    pages.append(st.Page("pages/dashboard.py", title="Évaluation"))

navigation = st.navigation(pages)
navigation.run()
