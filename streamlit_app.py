import streamlit as st
from openai import OpenAI
from typing import List, Dict
import time
import base64
import streamlit.components.v1 as components
import html as html_mod

st.set_page_config(page_title="💬 나의 첫번째 챗봇", layout="wide")

st.title("💬 나의 첫번째 챗봇")
st.write(
    "OpenAI API 키를 입력하고 채팅을 시작하세요. "
    "우측 사이드바에서 AI 캐릭터 이미지(또는 URL)를 설정할 수 있습니다."
)

# Sidebar: settings for AI avatar / name and controls
with st.sidebar:
    st.header("AI 설정")
    ai_name = st.text_input("AI 이름", value="AI Assistant")
    ai_avatar_url = st.text_input(
        "AI 아바타 이미지 URL (비워두면 기본 이미지 사용)",
        value="https://i.pravatar.cc/150?img=12",
    )
    uploaded_avatar = st.file_uploader("로컬 이미지 업로드 (선택)", type=["png", "jpg", "jpeg"])

    st.markdown("---")
    st.markdown("히스토리 관리")
    persist_history = st.checkbox("대화 히스토리 유지", value=True)
    if st.button("새로운 대화 시작 (초기화)"):
        st.session_state.messages = []
        st.success("대화 히스토리를 초기화했습니다.")
    st.markdown("---")
    st.markdown("개발자: hangj11")

# Save uploaded avatar bytes and mime-type into session_state so it persists across reruns
if uploaded_avatar is not None:
    try:
        avatar_bytes = uploaded_avatar.read()
        st.session_state.uploaded_avatar_bytes = avatar_bytes
        # uploaded_avatar.type exists on UploadedFile-like object
        st.session_state.uploaded_avatar_mime = getattr(uploaded_avatar, "type", "image/png")
    except Exception:
        st.session_state.uploaded_avatar_bytes = None
        st.session_state.uploaded_avatar_mime = None

# Decide what to use for displaying avatar in main area and as per-message avatar
def get_avatar_data_url() -> str:
    # Returns a data URL (base64) if uploaded image exists, else returns ai_avatar_url (if https/http) or default
    if st.session_state.get("uploaded_avatar_bytes"):
        mime = st.session_state.get("uploaded_avatar_mime", "image/png") or "image/png"
        b64 = base64.b64encode(st.session_state["uploaded_avatar_bytes"]).decode("utf-8")
        return f"data:{mime};base64,{b64}"
    # If user provided an URL and looks valid, use it
    if ai_avatar_url and (ai_avatar_url.startswith("http://") or ai_avatar_url.startswith("https://") or ai_avatar_url.startswith("data:")):
        return ai_avatar_url
    # fallback default
    return "https://i.pravatar.cc/150?img=12"

ai_avatar_data_url = get_avatar_data_url()

# Show avatar under the title (centered)
cols = st.columns([1, 0.2, 2, 0.2, 1])
with cols[2]:
    try:
        st.image(ai_avatar_data_url, width=120, caption=ai_name)
    except Exception as e:
        st.warning(f"아바타 이미지를 불러올 수 없습니다: {e}")

# API key input
openai_api_key = st.text_input("OpenAI API Key", type="password", placeholder="sk-...")

if not openai_api_key:
    st.info("API 키를 필요로 합니다. 사이드바 또는 위의 입력란에 OpenAI API 키를 입력하세요.", icon="🗝️")
    st.stop()

# Instantiate client
client = OpenAI(api_key=openai_api_key)

# Ensure session_state.messages exists and persists if requested
if "messages" not in st.session_state or not persist_history:
    st.session_state.messages: List[Dict[str, str]] = [
        {"role": "system", "content": "You are a helpful assistant."}
    ]

# Chat display area
chat_area = st.container()

def render_message_with_fallback(role: str, content: str, avatar_url: str = None):
    """
    Try to render with st.chat_message(avatar=...), if not supported, fall back to custom HTML layout
    that shows circular avatar + speech bubble using components.html.
    """
    # First try st.chat_message with avatar param (works on Streamlit versions that support it)
    if role == "assistant":
        try:
            # Some streamlit versions accept avatar as url/bytes; try and let it fail if unsupported
            st.chat_message("assistant", avatar=avatar_url).markdown(content)
            return
        except Exception:
            # fall through to custom rendering
            pass
    elif role == "user":
        try:
            st.chat_message("user").markdown(content)
            return
        except Exception:
            pass

    # Fallback: render custom HTML block with circular avatar + message bubble.
    # Escape the content to avoid XSS
    safe_content = html_mod.escape(content).replace("\n", "<br/>")
    avatar_src = avatar_url or ""
    # Align differently for user vs assistant
    if role == "assistant":
        # avatar left, bubble right
        html_block = f"""
        <div style="display:flex; align-items:flex-start; gap:8px; margin:8px 0;">
          <img src="{avatar_src}" style="width:36px; height:36px; border-radius:50%; object-fit:cover;"/>
          <div style="background:#f1f3f5; padding:8px 12px; border-radius:12px; max-width:80%; color:#111;">
            {safe_content}
          </div>
        </div>
        """
    else:
        # user: bubble right, avatar right
        html_block = f"""
        <div style="display:flex; align-items:flex-start; gap:8px; margin:8px 0; justify-content:flex-end;">
          <div style="background:#e6f7ff; padding:8px 12px; border-radius:12px; max-width:80%; color:#111; text-align:left;">
            {safe_content}
          </div>
          <img src="{avatar_src}" style="width:36px; height:36px; border-radius:50%; object-fit:cover;"/>
        </div>
        """
    # Use components.html to render raw HTML. Height will adjust; set a reasonable min-height to avoid clipping.
    components.html(html_block, height=120, scrolling=False)

def render_messages():
    with chat_area:
        for msg in st.session_state.messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            # For assistant messages use ai_avatar_data_url; for user messages you could show user's avatar or omit
            avatar_for_message = ai_avatar_data_url if role == "assistant" else ""
            render_message_with_fallback(role, content, avatar_for_message)

# Input area (single input + send button)
input_col, send_col = st.columns([8,1])
with input_col:
    user_input = st.text_input("메시지를 입력하세요", key="user_input", placeholder="여기에 질문을 입력하고 보내기 버튼을 누르세요.")
with send_col:
    send = st.button("보내기")

# Render existing messages first
render_messages()

# Handle sending
if send and user_input:
    # Append user message
    st.session_state.messages.append({"role": "user", "content": user_input})
    render_messages()

    # Call OpenAI API
    try:
        with st.spinner("AI가 응답하는 중..."):
            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": m["role"], "content": m["content"]} for m in st.session_state.messages],
                temperature=0.7,
            )
            assistant_text = response.choices[0].message["content"]
            st.session_state.messages.append({"role": "assistant", "content": assistant_text})
            # small pause to ensure UI updates
            time.sleep(0.1)
            render_messages()
            # clear the input box
            st.session_state["user_input"] = ""
    except Exception as e:
        st.error(f"API 호출 중 오류가 발생했습니다: {e}")

if not st.session_state.messages:
    st.info("새로운 대화를 시작하세요. 메시지를 입력하고 '보내기'를 누르세요.")
