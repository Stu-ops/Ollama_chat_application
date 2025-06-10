import os
import asyncio
import json
from flask import Flask, request
from flask_socketio import SocketIO, emit, join_room, leave_room
from flask_cors import CORS
from dotenv import load_dotenv
import requests
import logging
from datetime import datetime
import threading
import time

# Load environment variables from .env file
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'your-secret-key-here')

# Enable CORS for all routes
CORS(app)

# Initialize SocketIO with proper CORS settings
socketio = SocketIO(app, cors_allowed_origins="*",async_mode='threading',) 

# Ollama configuration
OLLAMA_HOST = os.environ.get('OLLAMA_HOST', 'localhost')
OLLAMA_PORT = os.environ.get('OLLAMA_PORT', '11434')
OLLAMA_URL = f"http://{OLLAMA_HOST}:{OLLAMA_PORT}"
MODEL_NAME = os.environ.get('MODEL_NAME', 'llama3.2')

# Store active users and rooms
active_users = {}
chat_rooms = {'general': [], 'tech': [], 'random': []}

def wait_for_ollama():
    """Wait for Ollama to be ready"""
    max_retries = 10
    retry_count = 0
    
    while retry_count < max_retries:
        try:
            response = requests.get(f"{OLLAMA_URL}/api/tags", timeout=5)
            if response.status_code == 200:
                logger.info("✅ Ollama is ready!")
                return True
        except requests.exceptions.RequestException as e:
            logger.info(f"⏳ Waiting for Ollama... ({retry_count + 1}/{max_retries}) - {e}")
            time.sleep(2)
            retry_count += 1
    
    logger.warning("⚠️ Failed to connect to Ollama after maximum retries")
    return False

def pull_model():
    """Pull the required model if not available"""
    attempt=0
    start_time=time.time()
    try:
        # Check if model exists
        response = requests.get(f"{OLLAMA_URL}/api/tags", timeout=10)
        if response.status_code == 200:
            models = response.json().get('models', [])
            model_names = [model['name'] for model in models]
            
            if MODEL_NAME not in model_names and f"{MODEL_NAME}:latest" not in model_names:
                    while attempt <= 2:
                        attempt += 1
                        try:
                            logger.info(f"📥 Pulling model {MODEL_NAME} (attempt {attempt})...")
                            pr = requests.post(
                                f"{OLLAMA_URL}/api/pull",
                                json={"name": MODEL_NAME},
                                stream=True,
                                timeout=600,  # Increased timeout for large models
                            )
                            pr.raise_for_status()
                            # Drain the stream without logging each line
                            for _ in pr.iter_lines():
                                pass

                            total = time.time() - start_time
                            logger.info(f"✅ Model {MODEL_NAME} pulled successfully in {total:.1f}s (after {attempt} attempt(s))")
                            return True

                        except (requests.exceptions.Timeout, requests.exceptions.RequestException) as e:
                            now = time.time()-start_time
                            start_time = time.time()
                            logger.warning(f"⏳ Pull attempt {attempt} failed: {e} — in {now:.1f}s")

                    # If we exit the loop, we ran out of time
                    elapsed = time.time() - start_time
                    logger.error(f"❌ Failed to pull model {MODEL_NAME} within {elapsed:.1f}s")
                    return False
            else:
                logger.info(f"✅ Model {MODEL_NAME} already available")
                
    except Exception as e:
        logger.error(f"❌ Error pulling model: {e}")

def generate_llm_response(prompt, conversation_history=""):
    """Generate response from Ollama LLM"""
    try:
        # Prepare the full context
        full_prompt = f"{conversation_history}\nUser: {prompt}\nAssistant:"
        
        payload = {
            "model": MODEL_NAME,
            "prompt": full_prompt,
            "stream": False,
            "options": {
                "temperature": 0.7,
                "num_predict": 500
            }
        }
        
        response = requests.post(
            f"{OLLAMA_URL}/api/generate",
            json=payload,
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            return result.get('response', 'Sorry, I could not generate a response.')
        else:
            logger.error(f"❌ Ollama API error: {response.status_code}")
            return "Sorry, I'm having trouble connecting to the AI model."
            
    except requests.exceptions.Timeout:
        logger.error("⏰ Ollama API timeout")
        return "Sorry, the AI model is taking too long to respond."
    except Exception as e:
        logger.error(f"❌ Error generating LLM response: {e}")
        return "Sorry, I encountered an error while generating a response."

@socketio.on('connect')
def handle_connect():
    logger.info(f"✅ Client {request.sid} connected successfully")
    emit('status', {'msg': 'Connected to chat server'})

@socketio.on('disconnect')
def handle_disconnect():
    logger.info(f"🔌 Client disconnected: {request.sid}")
    
    # Remove user from active users and rooms
    if request.sid in active_users:
        user_info = active_users[request.sid]
        username = user_info['username']
        room = user_info['room']
        
        # Remove from room
        if room in chat_rooms and request.sid in chat_rooms[room]:
            chat_rooms[room].remove(request.sid)
            logger.info(f"👋 Removed {username} from room {room}")
        
        # Remove from active users
        del active_users[request.sid]
        
        # Notify room about user leaving
        emit('user_left', {
            'username': username,
            'timestamp': datetime.now().isoformat()
        }, room=room)
        
        logger.info(f"👋 User {username} left room {room}")
    
    print(f"❌ Client {request.sid} disconnected")

@socketio.on('join')
def handle_join(data):
    username = data.get('username', '').strip()
    room = data.get('room', 'general').strip()
    
    logger.info(f"🚪 Join request from {request.sid}: username={username}, room={room}")
    
    # Validate room name (not be needed if frontend ensures valid room names)
    if not username:
        logger.warning(f"❌ Empty username from {request.sid}")
        emit('error', {'msg': 'Username is required'})
        return
    
    # Remove user from previous room if they were in one
    if request.sid in active_users:
        old_room = active_users[request.sid]['room']
        if old_room in chat_rooms and request.sid in chat_rooms[old_room]:
            chat_rooms[old_room].remove(request.sid)
            leave_room(old_room)
            logger.info(f"🔄 Moved {username} from {old_room} to {room}")
    
    # Store user info
    active_users[request.sid] = {
        'username': username,
        'room': room,
        'joined_at': datetime.now().isoformat()
    }
    
    # Add to room
    join_room(room)
    if room not in chat_rooms:
        chat_rooms[room] = []
    
    if request.sid not in chat_rooms[room]:
        chat_rooms[room].append(request.sid)
    
    # Send welcome message to user first
    emit('message', {
        'username': 'System',
        'message': f'Welcome to {room} room, {username}!',
        'timestamp': datetime.now().isoformat(),
        'type': 'system'
    })
    
    # Notify room about new user (exclude the user who just joined)
    emit('user_joined', {
        'username': username,
        'timestamp': datetime.now().isoformat()
    }, room=room, include_self=False)
    
    # Send room info to user
    room_users = []
    for sid in chat_rooms[room]:
        if sid in active_users:
            room_users.append(active_users[sid]['username'])
    
    emit('room_info', {
        'room': room,
        'users': room_users,
        'user_count': len(room_users)
    })
    
    logger.info(f"✅ User {username} successfully joined room {room}. Room now has {len(room_users)} users.")

@socketio.on('message')
def handle_message(data):
    if request.sid not in active_users:
        logger.warning(f"❌ Message from non-joined user: {request.sid}")
        emit('error', {'msg': 'You must join a room first'})
        return
    
    user_info = active_users[request.sid]
    username = user_info['username']
    room = user_info['room']
    message = data.get('message', '').strip()
    
    if not message:
        emit('error', {'msg': 'Message cannot be empty'})
        return
    
    timestamp = datetime.now().isoformat()
    
    # Broadcast user message to room
    message_data = {
        'username': username,
        'message': message,
        'timestamp': timestamp,
        'type': 'user'
    }
    
    emit('message', message_data, room=room)
    logger.info(f"💬 Message from {username} in {room}: {message[:50]}...")
    
    # Check if message is directed to AI
    should_trigger_ai = (
        message.lower().startswith('@ai') or 
        '@ai' in message.lower())
    
    if should_trigger_ai:
        # Generate AI response in a separate thread
        def generate_and_send_ai_response():
            try:
                # Prepare AI prompt
                ai_prompt = message.replace('@ai', '').strip()
                if not ai_prompt:
                    ai_prompt = message
                
                logger.info(f"🤖 Generating AI response for: {ai_prompt[:50]}...")
                ai_response = generate_llm_response(ai_prompt)
                
                # Send AI response
                ai_message_data = {
                    'username': 'AI Assistant',
                    'message': ai_response,
                    'timestamp': datetime.now().isoformat(),
                    'type': 'ai'
                }
                
                socketio.emit('message', ai_message_data, room=room)
                logger.info(f"🤖 AI response sent to room {room}")
                
            except Exception as e:
                logger.error(f"❌ Error generating AI response: {e}")
                error_message = {
                    'username': 'AI Assistant',
                    'message': 'Sorry, I encountered an error while processing your request.',
                    'timestamp': datetime.now().isoformat(),
                    'type': 'ai'
                }
                socketio.emit('message', error_message, room=room)
        
        # Start AI response generation in background
        ai_thread = threading.Thread(target=generate_and_send_ai_response, daemon=True).start()

@socketio.on('get_rooms')
def handle_get_rooms():
    """Get list of available rooms"""
    rooms_info = {}
    for room, user_sids in chat_rooms.items():
        active_users_in_room = [active_users[sid]['username'] for sid in user_sids if sid in active_users]
        rooms_info[room] = {
            'user_count': len(active_users_in_room),
            'users': active_users_in_room
        }
    
    emit('rooms_list', rooms_info)

@app.route('/health')
def health_check():
    return {
        'status': 'healthy', 'timestamp': datetime.now().isoformat()}

@app.route('/ollama-status')
def ollama_status():
    try:
        response = requests.get(f"{OLLAMA_URL}/api/tags", timeout=5)
        if response.status_code == 200:
            return {'status': 'connected', 'models': response.json()}
        else:
            return {'status': 'error', 'code': response.status_code}
    except Exception as e:
        return {'status': 'disconnected', 'error': str(e)}

@app.route('/rooms')
def get_rooms():
    """REST endpoint to get room information"""
    rooms_info = {}
    for room, user_sids in chat_rooms.items():
        active_users_in_room = [active_users[sid]['username'] for sid in user_sids if sid in active_users]
        rooms_info[room] = {
            'user_count': len(active_users_in_room),
            'users': active_users_in_room
        }
    
    return rooms_info

if __name__ == '__main__':
    logger.info("🚀 Starting Ollama Chat Server...")
    
    # Wait for Ollama to be ready (optional - can start without Ollama)
    if wait_for_ollama():
        # Pull required model
        pull_model()
        logger.info("Ollama is ready and model is available")
    else:
        logger.warning("Starting server without Ollama - AI features will be disabled")
    
    # Start the server
    logger.info(f"Starting server on port 5000")
    socketio.run(app, host='0.0.0.0', port=5000, debug=False, allow_unsafe_werkzeug=True)