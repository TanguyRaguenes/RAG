import streamlit as st

from app.services.auth_service import handle_oidc_callback

handle_oidc_callback()

# --- CONFIGURATION DE LA NAVIGATION ---
# C'est ici que vous définissez les titres et les icônes
pages = [
    st.Page("pages/chat.py", title="Discussion", icon="💬", default=True),
    st.Page("pages/Dashboard.py", title="Tableau de bord", icon="📊"),
]

# --- LANCEMENT ---
pg = st.navigation(pages)
pg.run()
