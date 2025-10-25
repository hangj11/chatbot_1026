import streamlit as st
from openai import OpenAI
from typing import List, Dict, Any
import time
import base64
import streamlit.components.v1 as components
import html as html_mod
import traceback
import requests
import json

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

def extract_assistant_text_from_response(resp: Any) -> str:
    """
    Extract assistant content from response object/dict in a robust way.
    """
    try:
        # Try attribute-style choices
        choices = getattr(resp, "choices", None)
        if choices is None:
            # Try dict-style
            if isinstance(resp, dict):
                choices = resp.get("choices", None)
            else:
                choices = None
        if not choices:
            return ""
        first_choice = choices[0]
        # first_choice might be an object with .message or a dict with 'message'
        msg = None
        if hasattr(first_choice, "message"):
            msg = getattr(first_choice, "message")
        elif isinstance(first_choice, dict):
            msg = first_choice.get("message", None)

        if msg is None:
            # maybe 'text' field exists
            if isinstance(first_choice, dict):
                return first_choice.get("text") or first_choice.get("message") or ""
            return str(first_choice)

        # If msg is dict
        if isinstance(msg, dict):
            return msg.get("content", "") or msg.get("text", "") or ""
        # If msg is object with attribute 'content' or 'text'
        if hasattr(msg, "content"):
            return getattr(msg, "content") or getattr(msg, "text", "") or ""
        if hasattr(msg, "text"):
            return getattr(msg, "text", "")
        # fallback
        return str(msg)
    except Exception:
        st.error("응답 처리 중 예외가 발생했습니다. 콘솔 로그를 확인하세요.")
        st.write(traceback.format_exc())
        return ""

def render_message_with_fallback(role: str, content: str, avatar_url: str = None):
    """
    Try st.chat_message with avatar; fallback to custom HTML block for max compatibility.
    """
    # First try st.chat_message with avatar param (works on Streamlit versions that support it)
    if role == "assistant":
        try:
            st.chat_message("assistant", avatar=avatar_url).markdown(content)
            return
        except Exception:
            pass
    elif role == "user":
        try:
            st.chat_message("user").markdown(content)
            return
        except Exception:
            pass

    # Fallback: custom HTML
    safe_content = html_mod.escape(content).replace("\n", "<br/>")
    avatar_src = avatar_url or ""
    if role == "assistant":
        html_block = f"""
        <div style="display:flex; align-items:flex-start; gap:8px; margin:8px 0;">
          <img src="{avatar_src}" style="width:36px; height:36px; border-radius:50%; object-fit:cover;"/>
          <div style="background:#f1f3f5; padding:8px 12px; border-radius:12px; max-width:80%; color:#111;">
            {safe_content}
          </div>
        </div>
        """
    else:
        html_block = f"""
        <div style="display:flex; align-items:flex-start; gap:8px; margin:8px 0; justify-content:flex-end;">
          <div style="background:#e6f7ff; padding:8px 12px; border-radius:12px; max-width:80%; color:#111; text-align:left;">
            {safe_content}
          </div>
          <img src="{avatar_src}" style="width:36px; height:36px; border-radius:50%; object-fit:cover;"/>
        </div>
        """
    components.html(html_block, height=120, scrolling=False)

def render_messages():
    with chat_area:
        for msg in st.session_state.messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
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

# Helper: fallback direct HTTP call using requests to avoid httpx header-encoding issues
def call_openai_via_requests(api_key: str, messages_payload: List[Dict[str, str]], model: str = "gpt-3.5-turbo", temperature: float = 0.7, timeout: int = 60) -> Dict[str, Any]:
    url = "https://api.openai.com/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        # Keep headers ASCII-only; do not include non-ascii values here
    }
    body = {
        "model": model,
        "messages": messages_payload,
        "temperature": temperature,
    }
    resp = requests.post(url, headers=headers, json=body, timeout=timeout)
    resp.raise_for_status()
    return resp.json()

# Handle sending
if send and user_input:
    # Append user message
    st.session_state.messages.append({"role": "user", "content": user_input})
    render_messages()

    # Prepare payload
    messages_payload = [{"role": m["role"], "content": m["content"]} for m in st.session_state.messages]

    # Attempt normal client call first; if header encoding error occurs, fall back to requests
    try:
        with st.spinner("AI가 응답하는 중..."):
            try:
                response = client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=messages_payload,
                    temperature=0.7,
                )
                assistant_text = extract_assistant_text_from_response(response)
            except Exception as e:
                # Detect encoding-related error (ascii codec can't encode ...) or other httpx header issues
                tb = traceback.format_exc()
                if isinstance(e, UnicodeEncodeError) or "ascii" in str(e).lower() or "header" in str(e).lower() or "httpx" in tb.lower():
                    # Fallback to requests
                    try:
                        resp_json = call_openai_via_requests(openai_api_key, messages_payload, model="gpt-3.5-turbo", temperature=0.7)
                        assistant_text = extract_assistant_text_from_response(resp_json)
                    except Exception as ex_req:
                        st.error(f"폴백 요청도 실패했습니다: {ex_req}")
                        st.write(traceback.format_exc())
                        assistant_text = ""
                else:
                    # Other exception: re-raise to outer except
                    raise

            if not assistant_text:
                st.error("응답에서 텍스트를 추출할 수 없습니다. API 응답 구조를 확인해 주세요.")
            else:
                st.session_state.messages.append({"role": "assistant", "content": assistant_text})
            # small pause to ensure UI updates
            time.sleep(0.1)
            render_messages()
            # clear the input box
            st.session_state["user_input"] = ""
    except Exception as e:
        st.error(f"API 호출 중 오류가 발생했습니다: {e}")
        st.write(traceback.format_exc())

if not st.session_state.messages:
    st.info("새로운 대화를 시작하세요. 메시지를 입력하고 '보내기'를 누르세요.")
