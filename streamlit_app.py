import streamlit as st
from openai import OpenAI
from typing import List, Dict
import time

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
    if uploaded_avatar is not None:
        # If user uploads an image, it will be used directly as bytes by streamlit's chat_message
        ai_avatar_source = uploaded_avatar
    else:
        ai_avatar_source = ai_avatar_url

    st.markdown("---")
    st.markdown("히스토리 관리")
    persist_history = st.checkbox("대화 히스토리 유지", value=True)
    if st.button("새로운 대화 시작 (초기화)"):
        st.session_state.messages = []
        st.success("대화 히스토리를 초기화했습니다.")
    st.markdown("---")
    st.markdown("개발자: hangj11")

# API key input
openai_api_key = st.text_input("OpenAI API Key", type="password", placeholder="sk-...")

if not openai_api_key:
    st.info("API 키를 필요로 합니다. 사이드바 또는 위의 입력란에 OpenAI API 키를 입력하세요.", icon="🗝️")
    st.stop()

# Instantiate client
client = OpenAI(api_key=openai_api_key)

# Ensure session_state.messages exists and persists if requested
if "messages" not in st.session_state or not persist_history:
    # initialize with an optional friendly system message or empty
    st.session_state.messages: List[Dict[str, str]] = [
        {"role": "system", "content": "You are a helpful assistant."}
    ]

# Chat display area
chat_area = st.container()

def render_messages():
    with chat_area:
        for msg in st.session_state.messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            if role == "assistant":
                # show assistant message with avatar
                # st.chat_message supports `avatar` parameter (Streamlit >= 1.22). If this isn't available,
                # Streamlit will ignore the avatar param but still display the message.
                try:
                    st.chat_message("assistant", avatar=ai_avatar_source).markdown(content)
                except TypeError:
                    # fallback if streamlit version doesn't support passing avatar as argument object
                    st.chat_message("assistant").markdown(content)
            elif role == "user":
                st.chat_message("user").markdown(content)
            else:
                # system or other roles - render as info
                st.info(content)

# Input area (keep a single input area instead of showing a "Start Chat" button repeatedly)
input_col, send_col = st.columns([8,1])
with input_col:
    user_input = st.text_input("메시지를 입력하세요", key="user_input", placeholder="여기에 질문을 입력하고 보내기 버튼을 누르세요.")
with send_col:
    send = st.button("보내기")

# Render existing messages first
render_messages()

# Handle sending
if send and user_input:
    # append user message
    st.session_state.messages.append({"role": "user", "content": user_input})
    # re-render to show user's message immediately
    render_messages()

    # Call OpenAI API
    try:
        with st.spinner("AI가 응답하는 중..."):
            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": m["role"], "content": m["content"]} for m in st.session_state.messages],
                temperature=0.7,
            )
            # get assistant text
            assistant_text = response.choices[0].message["content"]
            # append assistant reply to history
            st.session_state.messages.append({"role": "assistant", "content": assistant_text})
            # small pause to ensure UI updates in order
            time.sleep(0.1)
            render_messages()
    except Exception as e:
        st.error(f"API 호출 중 오류가 발생했습니다: {e}")

# Ensure chat history is shown after all actions
if not st.session_state.messages:
    st.info("새로운 대화를 시작하세요. 메시지를 입력하고 '보내기'를 누르세요.")
