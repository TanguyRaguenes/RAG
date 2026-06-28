import streamlit as st

from app.services.auth_service import handle_oidc_callback

st.set_page_config(page_title="IsiDore", layout="wide")

handle_oidc_callback()

pages = [
    st.Page("pages/chat.py", title="Discussion", default=True),
    st.Page("pages/dashboard.py", title="Évaluation"),
]

pg = st.navigation(pages)
pg.run()
