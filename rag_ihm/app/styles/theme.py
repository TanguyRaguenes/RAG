import streamlit as st

from app.state.session_state import UI_THEME_KEY, get_theme_mode


THEME_OPTIONS = ["Sombre", "Clair"]


def render_theme_selector() -> None:
    """Affiche le choix de thème dans la sidebar."""
    current_mode = get_theme_mode()
    index = THEME_OPTIONS.index(current_mode) if current_mode in THEME_OPTIONS else 0
    st.radio(
        "Apparence",
        THEME_OPTIONS,
        index=index,
        horizontal=True,
        key=UI_THEME_KEY,
    )


def apply_theme() -> None:
    """Applique un thème visuel clair ou sombre au-dessus du thème Streamlit."""
    palette = _palette(get_theme_mode())
    st.markdown(
        f"""
        <style>
        .stApp {{
            background: {palette["background"]};
            color: {palette["text"]};
        }}

        .stApp, .stApp p, .stApp span, .stApp label,
        .stApp h1, .stApp h2, .stApp h3, .stApp h4,
        .stApp small, .stApp strong,
        [data-testid="stMarkdownContainer"],
        [data-testid="stWidgetLabel"] {{
            color: {palette["text"]} !important;
        }}

        [data-testid="stSidebar"] {{
            background: {palette["sidebar"]};
        }}

        [data-testid="stSidebar"] * {{
            color: {palette["text"]};
        }}

        [data-testid="stHeader"] {{
            background: transparent;
        }}

        [data-testid="stChatMessage"] {{
            background: {palette["surface"]};
            border: 1px solid {palette["border"]};
            border-radius: 18px;
        }}

        [data-testid="stExpander"] {{
            background: {palette["surface"]};
            border: 1px solid {palette["border"]};
            border-radius: 14px;
        }}

        [data-testid="stExpander"] > details {{
            background: {palette["surface"]} !important;
            border-radius: 14px;
        }}

        [data-testid="stExpander"] summary,
        [data-testid="stExpander"] summary *,
        [data-testid="stExpander"] details,
        [data-testid="stExpander"] details *,
        [data-testid="stExpander"] [data-testid="stMarkdownContainer"],
        [data-testid="stExpander"] [data-testid="stMarkdownContainer"] *,
        [data-testid="stExpander"] svg {{
            color: {palette["text"]} !important;
            fill: {palette["text"]} !important;
        }}

        [data-testid="stExpander"] summary {{
            background: {palette["surface"]} !important;
            border-radius: 14px !important;
            outline: none !important;
            box-shadow: none !important;
        }}

        [data-testid="stExpander"] summary:hover,
        [data-testid="stExpander"] summary:focus,
        [data-testid="stExpander"] summary:focus-visible,
        [data-testid="stExpander"] summary:active,
        [data-testid="stExpander"] details[open] summary {{
            background: {palette["surface_active"]} !important;
            color: {palette["text"]} !important;
            outline: none !important;
            box-shadow: none !important;
        }}

        [data-testid="stExpander"] summary:hover *,
        [data-testid="stExpander"] summary:focus *,
        [data-testid="stExpander"] summary:focus-visible *,
        [data-testid="stExpander"] summary:active *,
        [data-testid="stExpander"] details[open] summary * {{
            background: transparent !important;
            color: {palette["text"]} !important;
            fill: {palette["text"]} !important;
        }}

        [data-testid="stExpander"] div {{
            background-color: transparent !important;
        }}

        hr,
        [data-testid="stDivider"],
        [data-testid="stDivider"] * {{
            border-color: {palette["divider"]} !important;
            color: {palette["divider"]} !important;
        }}

        .stButton > button {{
            border-radius: 12px;
            border: 1px solid {palette["border"]};
            background: {palette["button"]};
            color: {palette["text"]};
        }}

        .stButton > button:hover {{
            border-color: #FF6D5A;
            color: #FF6D5A;
        }}

        .stLinkButton > a {{
            border-radius: 14px;
            border: 1px solid #FF6D5A;
            background: #FF6D5A;
            color: #FFFFFF !important;
            font-weight: 700;
        }}

        textarea, input,
        [data-baseweb="input"],
        [data-baseweb="textarea"],
        [data-testid="stChatInput"] textarea {{
            background: {palette["input"]} !important;
            color: {palette["text"]} !important;
            border-color: {palette["border"]} !important;
            caret-color: #FF6D5A !important;
        }}

        textarea:focus,
        input:focus,
        [data-testid="stChatInput"] textarea:focus {{
            outline: 2px solid #FF6D5A !important;
            border-color: #FF6D5A !important;
            box-shadow: 0 0 0 3px rgba(255, 109, 90, 0.22) !important;
            caret-color: #FF6D5A !important;
        }}

        textarea::placeholder, input::placeholder,
        [data-testid="stChatInput"] textarea::placeholder {{
            color: {palette["muted"]} !important;
            opacity: 1;
        }}

        [data-testid="stChatInput"] {{
            background: {palette["background"]} !important;
        }}

        [data-testid="stChatInput"] > div,
        [data-testid="stChatInput"] form,
        [data-testid="stChatInput"] section,
        [data-testid="stChatInput"] div[data-baseweb="textarea"] {{
            background: {palette["input"]} !important;
            border-color: {palette["border"]} !important;
        }}

        [data-testid="stChatInput"]:focus-within > div,
        [data-testid="stChatInput"] form:focus-within,
        [data-testid="stChatInput"] section:focus-within,
        [data-testid="stChatInput"] div[data-baseweb="textarea"]:focus-within {{
            border-color: #FF6D5A !important;
            box-shadow: 0 0 0 3px rgba(255, 109, 90, 0.22) !important;
        }}

        textarea::selection,
        input::selection,
        [data-testid="stChatInput"] textarea::selection {{
            background: rgba(255, 109, 90, 0.35) !important;
            color: {palette["text"]} !important;
        }}

        [data-testid="stBottomBlockContainer"],
        [data-testid="stChatFloatingInputContainer"] {{
            background: {palette["background"]} !important;
        }}

        [data-baseweb="radio"] *,
        [data-baseweb="checkbox"] *,
        [data-testid="stCheckbox"] *,
        [data-testid="stToggle"] *,
        [role="switch"],
        [role="switch"] * {{
            color: {palette["text"]} !important;
        }}

        [role="switch"] {{
            background: {palette["switch_off"]} !important;
            border: 1px solid {palette["switch_border"]} !important;
            box-shadow: inset 0 0 0 1px {palette["switch_border"]} !important;
        }}

        [role="switch"][aria-checked="true"] {{
            background: #FF6D5A !important;
            border-color: #FF6D5A !important;
        }}

        [role="switch"] div,
        [role="switch"] span,
        [data-testid="stToggle"] div[role="switch"] div,
        [data-testid="stToggle"] div[role="switch"] span {{
            background: {palette["switch_thumb"]} !important;
            border-color: {palette["switch_thumb"]} !important;
        }}

        [role="switch"][aria-checked="true"] div,
        [role="switch"][aria-checked="true"] span {{
            background: #FFFFFF !important;
            border-color: #FFFFFF !important;
        }}

        [data-testid="stChatMessageAvatar"],
        [data-testid="stChatMessageAvatarUser"],
        [data-testid="stChatMessageAvatarAssistant"] {{
            background: {palette["avatar"]} !important;
            color: {palette["avatar_text"]} !important;
            border: 1px solid {palette["border"]};
        }}

        [data-testid="stChatMessageAvatar"] svg,
        [data-testid="stChatMessageAvatarUser"] svg,
        [data-testid="stChatMessageAvatarAssistant"] svg {{
            fill: {palette["avatar_text"]} !important;
            color: {palette["avatar_text"]} !important;
        }}

        .api-toast-overlay {{
            position: fixed;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            z-index: 999999;
            width: min(420px, calc(100vw - 2rem));
            padding: 1.15rem 1.35rem;
            border-radius: 22px;
            text-align: center;
            font-size: 1.08rem;
            font-weight: 800;
            box-shadow: {palette["popup_shadow"]};
            animation-duration: 3.2s;
            animation-timing-function: ease;
            animation-fill-mode: forwards;
            pointer-events: none;
        }}

        .api-toast-success {{
            background: {palette["success_bg"]};
            border: 1px solid {palette["success"]};
            color: {palette["success_text"]} !important;
        }}

        .api-toast-error {{
            background: {palette["danger_bg"]};
            border: 1px solid {palette["danger"]};
            color: {palette["danger_text"]} !important;
        }}

        .auth-shell {{
            min-height: 70vh;
            display: flex;
            align-items: center;
            justify-content: center;
        }}

        .auth-card {{
            width: min(560px, 100%);
            padding: 2.25rem;
            border-radius: 28px;
            border: 1px solid {palette["border"]};
            background: {palette["surface"]};
            box-shadow: {palette["shadow"]};
        }}

        .auth-eyebrow {{
            color: #FF6D5A;
            font-size: 0.85rem;
            font-weight: 700;
            letter-spacing: 0.08em;
            text-transform: uppercase;
            margin-bottom: 0.75rem;
        }}

        .auth-title {{
            color: {palette["text"]};
            font-size: 2.2rem;
            font-weight: 800;
            margin-bottom: 0.75rem;
        }}

        .auth-copy {{
            color: {palette["muted"]};
            font-size: 1rem;
            margin-bottom: 1.5rem;
        }}

        .auth-button {{
            display: inline-flex;
            align-items: center;
            justify-content: center;
            width: 100%;
            min-height: 3rem;
            border-radius: 14px;
            background: #FF6D5A;
            color: #FFFFFF !important;
            font-weight: 800;
            text-decoration: none !important;
            border: 1px solid #FF6D5A;
        }}

        .auth-button:hover {{
            filter: brightness(1.05);
            color: #FFFFFF !important;
        }}

        blockquote {{
            border-left-color: #FF6D5A;
            color: {palette["muted"]};
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def _palette(mode: str) -> dict[str, str]:
    if mode == "Clair":
        return {
            "background": "#F8F5F0",
            "sidebar": "#FFFFFF",
            "surface": "#FFFFFF",
            "surface_active": "#F3ECE3",
            "border": "#E7DED3",
            "divider": "#D8CFC4",
            "button": "#FFFFFF",
            "input": "#FFFFFF",
            "switch_off": "#E7DED3",
            "switch_border": "#BCAFA1",
            "switch_thumb": "#211A2E",
            "text": "#211A2E",
            "muted": "#62566F",
            "avatar": "#F0E8DF",
            "avatar_text": "#3B2A52",
            "success": "#0F7B55",
            "success_bg": "#EAF8F1",
            "success_text": "#0B5F42",
            "danger": "#C2412D",
            "danger_bg": "#FFF0ED",
            "danger_text": "#9F2F22",
            "shadow": "0 24px 70px rgba(31, 20, 45, 0.12)",
            "popup_shadow": "0 30px 90px rgba(31, 20, 45, 0.22)",
        }

    return {
        "background": "#24113F",
        "sidebar": "#1B0D31",
        "surface": "#321A55",
        "surface_active": "#3D2463",
        "border": "#4B2C73",
        "divider": "#4B2C73",
        "button": "#321A55",
        "input": "#1B0D31",
        "switch_off": "#4B2C73",
        "switch_border": "#7B5BA6",
        "switch_thumb": "#FFFFFF",
        "text": "#FFFFFF",
        "muted": "#D7C8E8",
        "avatar": "#3B235F",
        "avatar_text": "#FFFFFF",
        "success": "#8BE8BE",
        "success_bg": "#143C35",
        "success_text": "#D6FFE9",
        "danger": "#FFB4A8",
        "danger_bg": "#4B1D37",
        "danger_text": "#FFE1DC",
        "shadow": "0 24px 70px rgba(0, 0, 0, 0.28)",
        "popup_shadow": "0 34px 100px rgba(0, 0, 0, 0.45)",
    }
