"""Samostatný Socket.IO server pro real-time komunikaci."""
import os

import django
import eventlet
import socketio
from django.db.models import Q
from django.utils import timezone

from quiz.models import QuizSession, QuestionRun

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "kahootapp.settings.dev")
django.setup()

sio = socketio.Server(cors_allowed_origins="*", async_mode="eventlet")
app = socketio.WSGIApp(sio)


def get_room_name(session_hash):
    """Vrátí název room pro session."""
    return f"session_{session_hash}"


def get_current_question_run(session):
    """Vrátí aktuálně běžící otázku v sezení."""
    now = timezone.now()
    return (
        session.question_runs
        .filter(starts_at__isnull=False)
        .filter(Q(ends_at__isnull=True) | Q(ends_at__gt=now))
        .order_by("order")
        .last()
    )


@sio.event
def connect(sid, environ):
    """Připojení klienta."""
    pass

@sio.event
def disconnect(sid):
    """Odpojení klienta."""
    pass


@sio.event
def join_session(sid, data):
    """Připojit se k session."""
    session_hash = data.get('hash')
    if not session_hash:
        return {'status': 'error', 'message': 'No hash provided'}
    
    try:
        session = QuizSession.objects.get(hash=session_hash, is_active=True)
        room_name = get_room_name(session_hash)
        sio.enter_room(sid, room_name)
        send_session_status(session_hash)
        return {'status': 'joined', 'room': room_name}
    except QuizSession.DoesNotExist:
        return {'status': 'error', 'message': 'Session not found'}
    except Exception as e:
        return {'status': 'error', 'message': str(e)}


@sio.event
def leave_session(sid, data):
    """Opustit session."""
    session_hash = data.get('hash')
    if session_hash:
        sio.leave_room(sid, get_room_name(session_hash))


def send_session_status(session_hash):
    """Odeslat stav session všem připojeným klientům."""
    try:
        session = QuizSession.objects.get(hash=session_hash)
        room_name = get_room_name(session_hash)
        
        if not session.is_active:
            sio.emit('session_state', {'state': 'finished'}, room=room_name)
            return
        
        current = get_current_question_run(session)
        if current:
            sio.emit('session_state', {'state': 'question', 'order': current.order}, room=room_name)
        else:
            sio.emit('session_state', {'state': 'waiting'}, room=room_name)
    except QuizSession.DoesNotExist:
        pass


@sio.event
def broadcast_session_state(sid, data):
    """Broadcast stav session z Django."""
    session_hash = data.get('hash')
    if session_hash:
        sio.emit('session_state', {
            'state': data.get('state'),
            'order': data.get('order')
        }, room=get_room_name(session_hash))


@sio.event
def broadcast_answer_update(sid, data):
    """Broadcast aktualizaci odpovědí z Django."""
    session_hash = data.get('hash')
    if session_hash:
        sio.emit('answer_update', {
            'question_order': data.get('question_order'),
            'answered_count': data.get('answered_count'),
            'total_participants': data.get('total_participants'),
            'all_answered': data.get('all_answered'),
            'answer_stats': data.get('answer_stats')
        }, room=get_room_name(session_hash))


if __name__ == '__main__':
    eventlet.wsgi.server(eventlet.listen(('0.0.0.0', 8001)), app)
