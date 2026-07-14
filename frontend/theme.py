"""
Single source of truth for VendorAI's look and feel.

Design language: an Indian street-market signboard — marigold, turmeric,
chili red, and deep banana-leaf teal. Includes its own light/dark toggle
(kept in st.session_state) so every custom element — not just Streamlit's
native widgets — actually switches, not just the page chrome.
"""
import streamlit as st

_FONTS = """
@import url('https://fonts.googleapis.com/css2?family=Fraunces:ital,wght@0,600;0,700;1,600&family=Inter:wght@400;500;600;700&family=IBM+Plex+Mono:wght@500;600&display=swap');
"""

_VARS_LIGHT = """
:root {
    --va-radius: 14px;
    --va-radius-sm: 10px;
    --va-shadow: 0 1px 2px rgba(70,40,10,0.08), 0 2px 10px rgba(70,40,10,0.10);
    --va-shadow-lg: 0 8px 24px rgba(70,40,10,0.16);

    --va-marigold: #F5940C;
    --va-marigold-deep: #D97706;
    --va-turmeric: #FFC145;
    --va-chili: #D62839;
    --va-teal: #0E6E5C;
    --va-teal-deep: #0A4F42;
    --va-indigo: #1B2A4A;

    --va-accent: var(--va-marigold);
    --va-accent-soft: #FFE9C2;
    --va-success-soft: #CFEDE1;
    --va-danger-soft: #F8D2D2;

    --va-bg: #FFF3DE;
    --va-bg-card: #FFFDF8;
    --va-border: rgba(27,42,74,0.12);
    --va-text: var(--va-indigo);
    --va-text-muted: #5B6472;

    --va-font-display: 'Fraunces', Georgia, serif;
    --va-font-body: 'Inter', -apple-system, sans-serif;
    --va-font-mono: 'IBM Plex Mono', monospace;
}
"""

_VARS_DARK = """
:root {
    --va-radius: 14px;
    --va-radius-sm: 10px;
    --va-shadow: 0 1px 2px rgba(0,0,0,0.3), 0 2px 10px rgba(0,0,0,0.35);
    --va-shadow-lg: 0 8px 24px rgba(0,0,0,0.45);

    --va-marigold: #FDA435;
    --va-marigold-deep: #E08420;
    --va-turmeric: #FFC145;
    --va-chili: #E8596A;
    --va-teal: #29A186;
    --va-teal-deep: #1B7A65;
    --va-indigo: #FDF4E3;

    --va-accent: var(--va-marigold);
    --va-accent-soft: #3A2A14;
    --va-success-soft: #123A31;
    --va-danger-soft: #3A1620;

    --va-bg: #14100C;
    --va-bg-card: #221B14;
    --va-border: rgba(253,244,227,0.12);
    --va-text: #FDF4E3;
    --va-text-muted: #B8AC9A;

    --va-font-display: 'Fraunces', Georgia, serif;
    --va-font-body: 'Inter', -apple-system, sans-serif;
    --va-font-mono: 'IBM Plex Mono', monospace;
}
"""

_BASE_CSS = """
<style>
%(fonts)s
%(vars)s

.stApp {
    background:
        radial-gradient(circle at 8%% 0%%, var(--va-accent-soft) 0%%, transparent 40%%),
        radial-gradient(circle at 95%% 15%%, var(--va-success-soft) 0%%, transparent 35%%),
        var(--va-bg);
}
html, body, [class*="css"] { font-family: var(--va-font-body); color: var(--va-text); }
.block-container { padding-top: 1.6rem; padding-bottom: 3rem; }
p, li, span, label { color: var(--va-text); }

/* ---------- Signboard hero ---------- */
.va-hero {
    background: linear-gradient(120deg, var(--va-marigold) 0%%, var(--va-marigold-deep) 55%%, var(--va-chili) 130%%);
    border-radius: var(--va-radius);
    padding: 34px 36px;
    margin-bottom: 26px;
    box-shadow: var(--va-shadow-lg);
    position: relative;
    overflow: hidden;
}
.va-hero::after {
    content: "";
    position: absolute; inset: 0;
    background: repeating-linear-gradient(135deg, rgba(255,255,255,0.06) 0 2px, transparent 2px 14px);
    pointer-events: none;
}
.va-hero h2 {
    margin: 0 0 8px 0;
    font-family: var(--va-font-display);
    font-weight: 700;
    font-style: italic;
    font-size: 2.1rem;
    color: #FFF9EE;
    letter-spacing: -0.01em;
}
.va-hero p { margin: 0; color: rgba(255,249,238,0.92) !important; font-size: 1.02rem; }

/* ---------- Cards (tinted, not plain white) ---------- */
.va-card {
    background: var(--va-accent-soft);
    border: 1px solid var(--va-border);
    border-left: 4px solid var(--va-marigold);
    border-radius: var(--va-radius);
    box-shadow: var(--va-shadow);
    padding: 20px 22px;
    margin-bottom: 14px;
}
.va-card.teal { background: var(--va-success-soft); border-left-color: var(--va-teal); }
.va-card.chili { background: var(--va-danger-soft); border-left-color: var(--va-chili); }
.va-card h3 { margin-top: 0; }

.va-muted { color: var(--va-text-muted) !important; font-size: 0.92rem; }

/* ---------- Price-tag badge ---------- */
.va-tag {
    display: inline-flex; align-items: center; gap: 6px;
    font-family: var(--va-font-mono);
    font-size: 0.74rem; font-weight: 600;
    padding: 3px 12px 3px 8px;
    border-radius: 0 999px 999px 0;
    background: var(--va-bg-card);
    color: var(--va-marigold-deep);
    letter-spacing: 0.02em;
    border: 1px solid rgba(217,119,6,0.3);
}
.va-tag::before {
    content: "";
    width: 6px; height: 6px; border-radius: 50%%;
    background: var(--va-bg); border: 1px solid rgba(217,119,6,0.4);
}
.va-tag.teal { color: var(--va-teal-deep); border-color: rgba(14,110,92,0.3); }

/* ---------- Chat bubbles ---------- */
.va-msg-row { display: flex; align-items: flex-start; gap: 10px; margin: 12px 0; animation: va-fade-in 0.18s ease-out; }
.va-msg-row.user { flex-direction: row-reverse; }
.va-avatar {
    width: 34px; height: 34px; border-radius: 50%%; flex-shrink: 0;
    display: flex; align-items: center; justify-content: center;
    font-family: var(--va-font-display); font-weight: 700; font-size: 0.85rem;
    color: #fff; box-shadow: var(--va-shadow);
}
.va-avatar.user { background: linear-gradient(135deg, var(--va-marigold), var(--va-chili)); }
.va-avatar.assistant { background: linear-gradient(135deg, var(--va-teal), var(--va-teal-deep)); }
.va-bubble {
    padding: 11px 15px;
    border-radius: var(--va-radius-sm);
    max-width: 72%%;
    line-height: 1.55;
    box-shadow: var(--va-shadow);
    color: var(--va-text) !important;
}
.va-bubble.user { background: var(--va-accent-soft); border-bottom-right-radius: 3px; }
.va-bubble.assistant {
    background: var(--va-bg-card);
    border: 1px solid var(--va-border);
    border-top: 2px dashed rgba(14,110,92,0.4);
    border-bottom-left-radius: 3px;
}

@keyframes va-fade-in { from { opacity: 0; transform: translateY(3px); } to { opacity: 1; transform: translateY(0); } }

/* ---------- Buttons ---------- */
.stButton>button {
    border-radius: var(--va-radius-sm) !important;
    font-weight: 600 !important;
    transition: transform 0.06s ease-in, box-shadow 0.15s ease;
}
.stButton>button:hover { box-shadow: var(--va-shadow); }
.stButton>button:active { transform: scale(0.97); }
button[kind="primary"] {
    background: var(--va-marigold) !important;
    border-color: var(--va-marigold-deep) !important;
}

/* ---------- Sidebar ---------- */
[data-testid="stSidebar"] {
    background: linear-gradient(180deg, var(--va-teal-deep) 0%%, var(--va-indigo) 100%%);
}
[data-testid="stSidebar"] * { color: #FDF4E3 !important; }
[data-testid="stSidebar"] input,
[data-testid="stSidebar"] textarea,
[data-testid="stSidebar"] select,
[data-testid="stSidebar"] .stTextInput input,
[data-testid="stSidebar"] .stSelectbox div[data-baseweb="select"] * {
    color: #1A1A1A !important;
}
[data-testid="stSidebar"] .stTextInput input::placeholder {
    color: #6B6B6B !important;
}
[data-testid="stSidebar"] .stButton>button {
    background: rgba(255,249,238,0.08) !important;
    border: 1px solid rgba(255,249,238,0.18) !important;
    color: #FDF4E3 !important;
}
[data-testid="stSidebar"] .stButton>button:hover { background: rgba(245,148,12,0.25) !important; }
</style>
"""


def inject_theme() -> None:
    """Call once at the top of every page, after st.set_page_config().
    Also renders the light/dark toggle in the sidebar (shared across pages
    via session_state), and injects CSS matching the chosen mode."""
    if "va_dark_mode" not in st.session_state:
        st.session_state.va_dark_mode = False

    with st.sidebar:
        st.session_state.va_dark_mode = st.toggle(
            "🌙 Dark mode", value=st.session_state.va_dark_mode, key="va_dark_toggle"
        )

    variant_vars = _VARS_DARK if st.session_state.va_dark_mode else _VARS_LIGHT
    st.markdown(_BASE_CSS % {"fonts": _FONTS, "vars": variant_vars}, unsafe_allow_html=True)


def hero(title: str, subtitle: str) -> None:
    st.markdown(
        f"""<div class="va-hero"><h2>{title}</h2><p>{subtitle}</p></div>""",
        unsafe_allow_html=True,
    )


def card_open(variant: str = "") -> None:
    st.markdown(f'<div class="va-card {variant}">', unsafe_allow_html=True)


def card_close() -> None:
    st.markdown("</div>", unsafe_allow_html=True)


def tag(text: str, variant: str = "") -> str:
    return f'<span class="va-tag {variant}">{text}</span>'


def avatar_html(role: str, initials: str) -> str:
    return f'<div class="va-avatar {role}">{initials}</div>'