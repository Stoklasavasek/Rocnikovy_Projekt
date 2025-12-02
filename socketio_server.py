"""
Socket.IO server pro real-time komunikaci
Spouští se jako samostatný proces
"""
import socketio
import eventlet
from django.core.wsgi import get_wsgi_application
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'kahootapp.settings.dev')
django.setup()

from quiz.models import QuizSession, QuestionRun
from django.utils import timezone
from django.db.models import Q

# Vytvoření Socket.IO serveru
sio = socketio.Server(cors_allowed_origins="*", async_mode='eventlet')
app = socketio.WSGIApp(sio)


@sio.event
def connect(sid, environ):
    """Připojení klienta"""
    pass


@sio.event
def disconnect(sid):
    """Odpojení klienta"""
    pass


@sio.event
def join_session(sid, data):
    """Připojit se k session"""
    session_hash = data.get('hash')
    if not session_hash:
        return {'status': 'error', 'message': 'No hash provided'}
    
    try:
        session = QuizSession.objects.get(hash=session_hash, is_active=True)
        room_name = f"session_{session_hash}"
        sio.enter_room(sid, room_name)
        
        # Odeslat aktuální stav
        send_session_status(session_hash)
        
        # Vrátit potvrzení
        return {'status': 'joined', 'room': room_name}
    except QuizSession.DoesNotExist:
        return {'status': 'error', 'message': 'Session not found'}
    except Exception as e:
        return {'status': 'error', 'message': str(e)}


@sio.event
def leave_session(sid, data):
    """Opustit session"""
    session_hash = data.get('hash')
    if session_hash:
        sio.leave_room(sid, f"session_{session_hash}")


def send_session_status(session_hash):
    """Odeslat stav session všem připojeným klientům"""
    try:
        session = QuizSession.objects.get(hash=session_hash)
        
        if not session.is_active:
            sio.emit('session_state', {'state': 'finished'}, room=f"session_{session_hash}")
            return
        
        now = timezone.now()
        current = (
            session.question_runs
            .filter(starts_at__isnull=False)
            .filter(Q(ends_at__isnull=True) | Q(ends_at__gt=now))
            .order_by("order")
            .last()
        )
        
        if current:
            state_data = {
                'state': 'question',
                'order': current.order
            }
            sio.emit('session_state', state_data, room=f"session_{session_hash}")
        else:
            sio.emit('session_state', {'state': 'waiting'}, room=f"session_{session_hash}")
    except QuizSession.DoesNotExist:
        pass


@sio.event
def broadcast_session_state(sid, data):
    """Broadcast stav session z Django"""
    session_hash = data.get('hash')
    if session_hash:
        room_name = f"session_{session_hash}"
        state_data = {
            'state': data.get('state'),
            'order': data.get('order')
        }
        sio.emit('session_state', state_data, room=room_name)


@sio.event
def broadcast_answer_update(sid, data):
    """Broadcast aktualizaci odpovědí z Django"""
    session_hash = data.get('hash')
    if session_hash:
        room_name = f"session_{session_hash}"
        answer_data = {
            'question_order': data.get('question_order'),
            'answered_count': data.get('answered_count'),
            'total_participants': data.get('total_participants'),
            'all_answered': data.get('all_answered'),
            'answer_stats': data.get('answer_stats')
        }
        
        sio.emit('answer_update', answer_data, room=room_name)


if __name__ == '__main__':
    # Spustit socket.io server na portu 8001
    # '0.0.0.0' umožní připojení zvenku kontejneru
    eventlet.wsgi.server(eventlet.listen(('0.0.0.0', 8001)), app)

