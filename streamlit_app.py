import streamlit as st
from openai import OpenAI

# Configure the page
st.set_page_config(page_title="💬 나의 첫번째 챗봇", page_icon="💬")

# Initialize session state
if "messages" not in st.session_state:
    st.session_state.messages = []

if "ai_name" not in st.session_state:
    st.session_state.ai_name = "Assistant"

if "ai_avatar_url" not in st.session_state:
    st.session_state.ai_avatar_url = None

# Sidebar for AI settings
with st.sidebar:
    st.header("AI Settings")
    
    # AI name configuration
    ai_name = st.text_input("AI Name", value=st.session_state.ai_name)
    if ai_name != st.session_state.ai_name:
        st.session_state.ai_name = ai_name
    
    # Avatar URL configuration
    avatar_url = st.text_input("Avatar URL", value=st.session_state.ai_avatar_url or "")
    if avatar_url != st.session_state.ai_avatar_url:
        st.session_state.ai_avatar_url = avatar_url if avatar_url else None
    
    # File uploader for avatar
    uploaded_file = st.file_uploader("Or upload avatar image", type=["png", "jpg", "jpeg"])
    if uploaded_file is not None:
        st.image(uploaded_file, caption="Avatar Preview", width=100)
        st.session_state.ai_avatar_url = uploaded_file
    
    # New conversation button
    if st.button("🔄 New Conversation"):
        st.session_state.messages = []
        st.rerun()
    
    st.divider()
    
    # OpenAI API key input
    openai_api_key = st.text_input("OpenAI API Key", type="password")

# Main chat interface
st.title("💬 나의 첫번째 챗봇")
st.write(
    "This is a simple chatbot that uses OpenAI's GPT-3.5 model to generate responses. "
    "To use this app, you need to provide an OpenAI API key in the sidebar."
)

# Display chat messages
for message in st.session_state.messages:
    if message["role"] == "user":
        with st.chat_message("user"):
            st.markdown(message["content"])
    else:
        # Use avatar for assistant messages
        avatar = st.session_state.ai_avatar_url if message["role"] == "assistant" else None
        with st.chat_message("assistant", avatar=avatar):
            st.markdown(message["content"])

# Chat input area
if not openai_api_key:
    st.info("Please add your OpenAI API key in the sidebar to continue.", icon="🗝️")
else:
    # Create two columns for input and send button
    col1, col2 = st.columns([5, 1])
    
    with col1:
        user_input = st.text_input("Your message:", key="user_input", label_visibility="collapsed", placeholder="Type your message here...")
    
    with col2:
        send_button = st.button("Send", type="primary", use_container_width=True)
    
    # Process user input when Send button is clicked
    if send_button and user_input:
        # Add user message to session state
        st.session_state.messages.append({"role": "user", "content": user_input})
        
        # Create OpenAI client
        client = OpenAI(api_key=openai_api_key)
        
        try:
            # Call OpenAI API without streaming
            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": m["role"], "content": m["content"]} 
                    for m in st.session_state.messages
                ]
            )
            
            # Extract assistant response
            assistant_message = response.choices[0].message.content
            
            # Add assistant message to session state
            st.session_state.messages.append({"role": "assistant", "content": assistant_message})
            
            # Rerun to refresh the display
            st.rerun()
            
        except Exception as e:
            st.error(f"An error occurred while calling the OpenAI API: {str(e)}")
            st.info("Please check your API key and try again.")
            # Remove the user message that failed
            st.session_state.messages.pop()
    
    elif send_button and not user_input:
        st.warning("Please enter a message before sending.")
