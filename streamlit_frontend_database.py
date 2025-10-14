import streamlit as st
from langgraph_backend_database import chatbot, retrive_all_threads 
from langchain_core.messages import HumanMessage
import uuid

# ---------------- Utility Functions ----------------
def generate_thread_id():
    return str(uuid.uuid4())

def add_thread(thread_id):
    if thread_id not in st.session_state['chat_thread']:
        st.session_state['chat_thread'].append(thread_id)

def reset_chat():
    """Start a new chat thread."""
    thread_id = generate_thread_id()
    st.session_state['thread_id'] = thread_id
    add_thread(thread_id)
    st.session_state['message_history'] = []
    st.session_state['conversations'][thread_id] = []  # create empty list for new chat

def load_conversation(thread_id):
    """Load conversation either from memory or backend."""
    if thread_id in st.session_state['conversations']:
        return st.session_state['conversations'][thread_id]
    else:
        # fallback: load from backend (optional)
        state = chatbot.get_state(config={'configurable': {'thread_id': thread_id}})
        values = getattr(state, "values", {})
        messages = values.get('messages', [])
        temp_messages = []
        for msg in messages:
            if isinstance(msg, HumanMessage):
                role = 'user'
            else:
                role = 'assistant'
            temp_messages.append({'role': role, 'content': msg.content})
        st.session_state['conversations'][thread_id] = temp_messages
        return temp_messages

# ---------------- Session Setup ----------------
if 'message_history' not in st.session_state:
    st.session_state['message_history'] = []

if 'thread_id' not in st.session_state:
    st.session_state['thread_id'] = generate_thread_id()

if 'chat_thread' not in st.session_state:
    st.session_state['chat_thread'] = retrive_all_threads()

if 'conversations' not in st.session_state:
    st.session_state['conversations'] = {}

add_thread(st.session_state['thread_id'])

# ---------------- Sidebar ----------------
st.sidebar.title('Chatbot')

if st.sidebar.button('New Chat'):
    reset_chat()

st.sidebar.header('My Conversations')

# Display existing threads
for thread in st.session_state['chat_thread'][::-1]:
    if st.sidebar.button(str(thread)):
        st.session_state['thread_id'] = thread
        st.session_state['message_history'] = load_conversation(thread)

# ---------------- Display Chat History ----------------
for message in st.session_state['message_history']:
    with st.chat_message(message['role']):
        st.text(message['content'])

# ---------------- Chat Input ----------------
user_input = st.chat_input('Type Here')

if user_input:
    thread_id = st.session_state['thread_id']
    CONFIG = {'configurable': {'thread_id': thread_id}}

    # ----- USER MESSAGE -----
    user_msg = {'role': 'user', 'content': user_input}
    st.session_state['message_history'].append(user_msg)
    st.session_state['conversations'].setdefault(thread_id, []).append(user_msg)

    with st.chat_message('user'):
        st.text(user_input)

    # ----- ASSISTANT MESSAGE -----
    with st.chat_message('assistant'):
        ai_message = st.write_stream(
            chunk.content for chunk, metadata in chatbot.stream(
                {'messages': [HumanMessage(content=user_input)]},
                config=CONFIG,
                stream_mode='messages'
            )
        )

    ai_msg = {'role': 'assistant', 'content': ai_message}
    st.session_state['message_history'].append(ai_msg)
    st.session_state['conversations'][thread_id].append(ai_msg)