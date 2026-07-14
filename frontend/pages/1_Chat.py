import time
import streamlit as st
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from frontend.theme import inject_theme, avatar_html
from frontend.utils.api_client import (
    send_chat_message,
    list_conversations,
    create_conversation,
    update_conversation,
    delete_conversation,
    get_conversation_messages,
    get_vendor,
    update_vendor_name,
)

st.set_page_config(page_title="VendorAI - Chat", page_icon="💬", layout="wide")
inject_theme()

try:
    _vendor = get_vendor()
    VENDOR_NAME = _vendor.get("name", "there")
except Exception:
    VENDOR_NAME = "there"

GREETING = f"Hello {VENDOR_NAME}! 👋 Tell me about a sale, an expense, or ask me anything about your business."

FOLLOWUP_BY_INTENT = {
    "add_sale": ["What's my profit today?", "What should I restock?"],
    "add_expense": ["Show this week's report", "What's my profit today?"],
    "check_profit": ["Show this week's report", "What should I restock?"],
    "check_report": ["What should I restock?", "How's my inventory looking?"],
    "check_inventory": ["What should I restock?", "Show this week's report"],
    "restock_suggestion": ["Show this week's report", "What's my profit today?"],
    "unknown": ["I sold 12 coconuts for 900 rupees", "What's my profit today?"],
}


def load_conversation(conv_id: int) -> None:
    """Pull a conversation's messages from the backend into session_state."""
    st.session_state.current_conversation_id = conv_id
    rows = get_conversation_messages(conv_id)
    msgs = [{"role": "assistant", "content": GREETING}]
    for r in rows:
        msgs.append({"role": "user", "content": r["message"]})
        msgs.append({"role": "assistant", "content": r["response"], "intent": r.get("intent")})
    st.session_state.messages = msgs


def start_new_chat() -> None:
    st.session_state.current_conversation_id = None
    st.session_state.messages = [{"role": "assistant", "content": GREETING}]


if "messages" not in st.session_state:
    start_new_chat()

try:
    conversations = list_conversations(q=st.session_state.get("chat_search", ""))
    backend_ok = True
except Exception:
    conversations = []
    backend_ok = False

# ---------------- Sidebar: conversation manager ----------------
with st.sidebar:
    st.markdown("### 💬 Conversations")
    if st.button("➕ New chat", use_container_width=True):
        start_new_chat()
        st.rerun()

    st.text_input("Search chats", key="chat_search", placeholder="Search...", label_visibility="collapsed")

    st.markdown("---")
    if not backend_ok:
        st.caption("⚠️ Backend unreachable — chat list unavailable.")
    elif not conversations:
        st.caption("No conversations yet. Say hi to start one!")
    else:
        for c in conversations:
            is_active = c["id"] == st.session_state.get("current_conversation_id")
            label = ("📌 " if c["pinned"] else "") + c["title"]
            row = st.columns([5, 1, 1, 1])
            if row[0].button(label, key=f"open_{c['id']}", use_container_width=True,
                              type="primary" if is_active else "secondary"):
                load_conversation(c["id"])
                st.rerun()
            if row[1].button("📌", key=f"pin_{c['id']}", help="Pin/unpin"):
                update_conversation(c["id"], pinned=not c["pinned"])
                st.rerun()
            if row[2].button("✏️", key=f"ren_{c['id']}", help="Rename"):
                st.session_state[f"renaming_{c['id']}"] = True
            if row[3].button("🗑️", key=f"del_{c['id']}", help="Delete"):
                delete_conversation(c["id"])
                if is_active:
                    start_new_chat()
                st.rerun()
            if st.session_state.get(f"renaming_{c['id']}"):
                new_title = st.text_input("New name", value=c["title"], key=f"rename_input_{c['id']}")
                if st.button("Save", key=f"save_{c['id']}"):
                    update_conversation(c["id"], title=new_title)
                    st.session_state[f"renaming_{c['id']}"] = False
                    st.rerun()

    st.markdown("---")
    st.markdown("### Settings")
    new_name = st.text_input("Your name", value=VENDOR_NAME, key="vendor_name_input")
    if new_name and new_name != VENDOR_NAME:
        if st.button("Save name"):
            try:
                update_vendor_name(new_name)
                st.rerun()
            except Exception:
                st.caption("⚠️ Couldn't save — is the backend running?")
    lang_map = {"Auto-detect": None, "English": "en", "Hindi": "hi", "Tamil": "ta"}
    lang_choice = st.selectbox("Language", list(lang_map.keys()), index=0)
    st.markdown("---")
    st.markdown("**Quick examples**")
    for ex in [
        "I sold 12 coconuts for 900 rupees",
        "bought onions for 250 and tomatoes for 400",
        "how much profit today?",
        "what should I restock?",
    ]:
        if st.button(ex, use_container_width=True, key=f"ex_{ex}"):
            st.session_state["pending_message"] = ex

# ---------------- Message rendering ----------------


def render_message(role: str, content: str) -> None:
    initials = "You" if role == "user" else "VA"
    st.markdown(
        f"""<div class="va-msg-row {role}">
            {avatar_html(role, initials)}
            <div class="va-bubble {role}">{content}</div>
        </div>""",
        unsafe_allow_html=True,
    )


for i, msg in enumerate(st.session_state.messages):
    render_message(msg.get("role", "assistant"), msg.get("content", ""))

# Suggested follow-ups, based on the last assistant intent
last_assistant = next((m for m in reversed(st.session_state.messages) if m.get("role") == "assistant" and m.get("intent")), None)
if last_assistant:
    suggestions = FOLLOWUP_BY_INTENT.get(last_assistant["intent"], [])
    if suggestions:
        st.markdown('<p class="va-muted">Suggested follow-ups</p>', unsafe_allow_html=True)
        cols = st.columns(len(suggestions))
        for col, s in zip(cols, suggestions):
            if col.button(s, key=f"sugg_{s}", use_container_width=True):
                st.session_state["pending_message"] = s

if hasattr(st, "audio_input"):
    with st.expander("🎤 Voice input (beta)"):
        audio_value = st.audio_input("Record a message (optional)", label_visibility="collapsed")
        if audio_value is not None:
            st.caption(
                "Voice captured. Wire this up to Whisper (or any speech-to-text API) in "
                "`backend/llm_service.py` — transcribe the audio bytes to text, then call "
                "`send_chat_message()` with the transcript, exactly like typed messages."
            )


def _stream_words(text: str):
    for word in text.split(" "):
        yield word + " "
        time.sleep(0.015)


def send_and_render(final_input: str, show_user_bubble: bool = True) -> None:
    if show_user_bubble:
        st.session_state.messages.append({"role": "user", "content": final_input})
        render_message("user", final_input)

    with st.spinner("Thinking..."):
        try:
            result = send_chat_message(
                final_input,
                lang_map[lang_choice],
                conversation_id=st.session_state.current_conversation_id,
            )
            reply = result["reply"]
            st.session_state.current_conversation_id = result.get("conversation_id")
        except Exception as e:
            reply = (
                f"⚠️ Couldn't reach the backend. Is it running? "
                f"(`uvicorn backend.main:app --reload`)\n\nError: {e}"
            )
            result = {"intent": "unknown", "data": None, "language": "en"}

    st.markdown(
        f'<div class="va-msg-row assistant">{avatar_html("assistant", "VA")}'
        f'<div class="va-bubble assistant">',
        unsafe_allow_html=True,
    )
    st.write_stream(_stream_words(reply))
    st.markdown("</div></div>", unsafe_allow_html=True)

    st.session_state.messages.append(
        {"role": "assistant", "content": reply, "intent": result.get("intent")}
    )

    msg_key = len(st.session_state.messages)
    with st.container(key=f"chat_actions_{msg_key}"):
        col1, col2, _ = st.columns([0.4, 0.4, 9.2], gap="small")
        with col1:
            if st.button("📋", key=f"copy_{msg_key}", help="Copy response"):
                st.toast("Response ready to copy from the box below")
                st.code(reply, language=None)
        with col2:
            if st.button("🔄", key=f"regen_{msg_key}", help="Regenerate response"):
                st.session_state.messages.pop()  # drop the last assistant reply
                send_and_render(final_input, show_user_bubble=False)
                st.rerun()


pending = st.session_state.pop("pending_message", None)
user_input = st.chat_input("Type a message... e.g. 'I sold 12 coconuts for 900 rupees'")
final_input = pending or user_input

if final_input:
    send_and_render(final_input)