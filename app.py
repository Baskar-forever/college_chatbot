import streamlit as st
from college_bot import College
from langchain_community.chat_message_histories import ChatMessageHistory

# Streamlit app
st.title("College Chatbot")

# Keep College and chat history isolated per user session.
if "college" not in st.session_state:
    st.session_state.college = College()

if "chat_history" not in st.session_state:
    st.session_state.chat_history = ChatMessageHistory()

college = st.session_state.college

# Initialize chat history (stores role, content, and optional images)
if "messages" not in st.session_state:
    st.session_state.messages = []

def render_message(message):
    """Render a single message with optional image."""
    with st.chat_message(message["role"]):
        # Show the best matching image first (like Google search result)
        images = message.get("images", [])
        if images:
            img = images[0]
            st.image(img["url"], caption=img["alt"], width=200)
        st.markdown(message["content"])

# Display chat messages from history on app rerun
for message in st.session_state.messages:
    render_message(message)

# React to user input
if prompt := st.chat_input("Ask something about the college..."):
    # Display user message
    with st.chat_message("user"):
        st.markdown(prompt)
    st.session_state.messages.append({"role": "user", "content": prompt})

    # Get bot response (returns text + images)
    response, images = college.chatbot_response(prompt, chat_history=st.session_state.chat_history)

    # Display assistant response with image
    assistant_msg = {"role": "assistant", "content": response, "images": images}
    render_message(assistant_msg)
    st.session_state.messages.append(assistant_msg)