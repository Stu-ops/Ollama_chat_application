import streamlit as st
import socketio
import queue
import time
import requests
from dotenv import load_dotenv
import os

#load envrionment variables
load_dotenv()

# --- Streamlit app configuration ---
# Configure Streamlit page
st.set_page_config(
    page_title="Ollama chit-Chat App",
    page_icon="💬",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- Configuration ---
BACKEND_HOST = os.environ.get('BACKEND_HOST', 'localhost')
BACKEND_PORT = os.environ.get('BACKEND_PORT', '5000')
SERVER_URL = f"http://{BACKEND_HOST}:{BACKEND_PORT}"

# --- Fetch existing rooms via REST once ---
if 'rooms_list' not in st.session_state:
    try:
        resp = requests.get(f"{SERVER_URL}/rooms")
        resp.raise_for_status()
        # server returns dict: {room: {user_count, users}, ...}
        st.session_state.rooms_list = list(resp.json().keys())
    except Exception as e:
        # fallback defaults
        st.session_state.rooms_list = ['general', 'tech', 'random']
        st.warning(f" 🏠 ❌ Could not fetch rooms, using defaults: {e}")

# --- Persistent Socket.IO client & message queue ---
if 'sio' not in st.session_state:
    st.session_state.sio = socketio.Client()
if 'msg_queue' not in st.session_state:
    st.session_state.msg_queue = queue.Queue()

sio = st.session_state.sio
msg_queue = st.session_state.msg_queue

# --- Socket.io event handlers ---
@sio.event
def connect():
    msg_queue.put({'type': 'system', 'message': '🌐 Connected to chat server'})
    sio.emit('get_rooms')

@sio.on('status')
def on_status(data):
    msg_queue.put({'type': 'system', 'message': data.get('msg', '')})

@sio.event
def disconnect():
    msg_queue.put({'type': 'system', 'message': '🔌 Disconnected from chat server'})

@sio.on('message')
def on_message(data):
    msg_queue.put({
        'type': data.get('type', 'user'),
        'username': data.get('username', 'Unknown'),
        'message': data.get('message', ''),
        'timestamp': data.get('timestamp', '')
    })

@sio.on('user_joined')
def on_user_joined(data):
    msg_queue.put({'type': 'system', 'message': f"👤 {data['username']} joined."})

@sio.on('user_left')
def on_user_left(data):
    msg_queue.put({'type': 'system', 'message': f"🚪 {data['username']} left."})

@sio.on('room_info')
def on_room_info(data):
    msg_queue.put({'type': 'update_participants', 'users': data.get('users', [])})

@sio.on('rooms_list')
def on_rooms_list(data):
    # data may be dict or list
    rooms = data.keys() if isinstance(data, dict) else data
    msg_queue.put({'type': 'update_rooms_list', 'rooms': list(rooms)})

# --- Initialize session state defaults ---
def init_state():
    defaults = {
        'username': '',
        'room': st.session_state.rooms_list[0] if st.session_state.rooms_list else 'general',
        'connected': False,
        'participants': [],
        'incoming_messages': []
    }
    for key, val in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = val

init_state()

# --- Backend health checks ---
def check_backend_status():
    """Check if backend is running"""
    try:
        response = requests.get(f"{SERVER_URL}/health", timeout=5)
        return response.status_code == 200
    except Exception as e:
        print(f"Backend check failed: {e}")
        return False

def check_ollama_status():
    """Check Ollama status through backend"""
    try:
        response = requests.get(f"{SERVER_URL}/ollama-status", timeout=5)
        if response.status_code == 200:
            return response.json()
        return None
    except Exception as e:
        print(f"Ollama check failed: {e}")
        return None

# --- UI Layout ---
st.title("💬 Ollama Chat - Application")
st.markdown("Welcome to the Ollama Chat App! Connect with others in real-time.")
with st.sidebar:
    st.header("⚙️ Settings")
    # Status indicators
    col1, col2, col3 = st.columns(3)
    with col1:
        backend_running = check_backend_status()
        if backend_running:
                st.success("🟢 Backend")
        else:
                st.error("🔴 Backend not running")
        
    with col2:
        ollama_status = check_ollama_status()
        if ollama_status and ollama_status.get('status') == 'connected':
                st.success("🟢 Ollama")
        else:
                st.error("🔴 Ollama not running")
        
    with col3:
        if st.session_state.connected:
                st.success("🟢 Connected")
        else:        
            st.warning("🟡 Disconnected")
        
    st.divider()
    
    if not st.session_state.connected:
        st.session_state.username = st.text_input("Username", st.session_state.username)
        rooms= st.session_state.rooms_list
        st.session_state.room = st.selectbox("Room", rooms, index=rooms.index(st.session_state.room))
        if st.button("Connect", type="primary", disabled=not backend_running):
            if st.session_state.username.strip():
                try:
                    sio.connect(SERVER_URL)
                    sio.emit('join', {'username': st.session_state.username, 'room': st.session_state.room})
                    st.session_state.connected = True
                except Exception as e:
                    st.error(f"Connection failed: {e}")
            else:
                st.warning("Enter a username.")
    else:
        st.markdown(f"**Logged in as:** {st.session_state.username}")
        st.markdown(f"**Current room:** {st.session_state.room}")
        if sio.connected and st.button("Refresh Rooms"):
            sio.emit('get_rooms')
        if st.button("Disconnect"):
            sio.disconnect()
            st.session_state.connected = False
    
    st.divider()
    # Instructions
    st.header("How to use")
    st.markdown("""
        1. Make sure backend is running (green status)
        2. Enter your username
        3. Select a room
        4. Click Connect
        5. Start chatting!
        
        **AI Features:**
        - Type @ai followed by your question
        - Ask questions to trigger AI responses
        - AI powered by Ollama LLM
        """)
    st.markdown("Made with ❤️ by Priyank Bansal")


# --- Process queued events ---
while not msg_queue.empty():
    evt = msg_queue.get()
    if evt['type'] == 'update_rooms_list':
        st.session_state.rooms_list = evt['rooms']
        # preserve selection if possible
        if st.session_state.room not in st.session_state.rooms_list:
            st.session_state.room = st.session_state.rooms_list[0]
    elif evt['type'] == 'update_participants':
        st.session_state.participants = evt['users']
    else:
        st.session_state.incoming_messages.append(evt)
        st.session_state.incoming_messages = st.session_state.incoming_messages[-150:]  # keep last 100 messages

# --- Display participants ---
if st.session_state.connected and sio.connected:
    st.subheader("👥 Participants")
    st.write(', '.join(st.session_state.participants) or 'No one here yet')

# --- Chat area & send ---
chat_area = st.empty()
if st.session_state.connected and sio.connected:
    user_msg = st.text_input("Your message:", key="user_input")
    if st.button("Send") and user_msg.strip():
        sio.emit('message', {'message': user_msg.strip()})
elif st.session_state.connected:
    st.info("🔄 Connecting to server...")
else:
    st.info("👈 Please connect using the sidebar to start chatting")

# Show features
st.subheader("Features")
col1, col2, col3 = st.columns(3)
        
with col1:
        st.markdown("""
            **🔄 Real-time Chat**
            - Instant messaging
            - Multiple rooms
            - User presence
        """)
        
with col2:
        st.markdown("""
            **🤖 AI Integration**
            - Ollama LLM
            - Smart responses
            - Context awareness
        """)
        
with col3:
        st.markdown("""
            **🛠️ Easy Setup**
            - Simple deployment
            - Docker support
            - Cross-platform
        """)

# --- Render chat messages ---
with chat_area.container():
    for msg in st.session_state.incoming_messages:
        ts = ''
        if t := msg.get('timestamp', ''):
            if 'T' in t:
                hh_mm = ':'.join(t.split('T')[-1].split(':')[:2])
                ts = f"[{hh_mm}]"
        name = msg.get('username', 'System')
        text = msg.get('message', '')
        icon = '🤖' if msg['type'] == 'ai' else ''
        st.markdown(f"*{ts}* **{icon + name}**: {text}")
# --- Footer ---