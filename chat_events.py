from flask_socketio import join_room, leave_room, send, emit

from extensions import socketio, db
from models import ChatSession, Message, safe_get
from datetime import datetime

# --- WebSockets Handlers ---

@socketio.on('connect')
def handle_connect():
    """Handles a new client connection."""
    # In a real app, you would authenticate the user's JWT here
    print(f'Client connected')

@socketio.on('disconnect')
def handle_disconnect():
    """Handles a client disconnection."""
    print('Client disconnected')

@socketio.on('join_chat')
def on_join(data):
    """Client requests to join a specific chat session room."""
    # data = {user_id: 123, session_id: 456}
    room = str(data['session_id'])
    join_room(room)
    emit('status', {'msg': f'User {data["user_id"]} has joined the chat.'}, room=room)

@socketio.on('send_message')
def handle_message(data):
    """Handles new messages, saves them, and emits to the room."""
    # Required data: session_id, sender_id, content
    
    # 1. Validate and Save to database
    if not all(k in data for k in ['session_id', 'sender_id', 'content']):
        return
        
    new_message = Message(
        session_id=data['session_id'],
        sender_id=data['sender_id'],
        content=data['content']
    )
    db.session.add(new_message)
    
    # Update the last_message_at timestamp on the session
    session = safe_get(ChatSession, data['session_id'])
    if session:
        session.last_message_at = datetime.utcnow()
    
    db.session.commit()
    
    # 2. Emit the message to all clients in the session room
    room = str(data['session_id'])
    emit(
        'new_message',
        {
            'session_id': data['session_id'],
            'sender_id': data['sender_id'],
            'content': data['content'],
            'timestamp': str(new_message.timestamp)
        }, 
        to=room
    )

@socketio.on('typing')
def handle_typing(data):
    """Sends a 'typing' status to the other user in the room."""
    # data = {session_id: 456, sender_id: 123}
    room = str(data['session_id'])
    emit('typing_status', {'sender_id': data['sender_id']}, room=room, include_self=False)
