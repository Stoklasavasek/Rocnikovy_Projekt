"""
Socket.IO handler pro real-time komunikaci v kvízech
Komunikuje s externím socket.io serverem
"""
import socketio
from .models import QuizSession, QuestionRun
from django.utils import timezone
from django.db.models import Q
import threading

# Klient pro připojení k socket.io serveru
socketio_client = None
_client_lock = threading.Lock()

def get_socketio_client():
    """Získat nebo vytvořit socket.io klienta"""
    global socketio_client
    with _client_lock:
        if socketio_client is None:
            socketio_client = socketio.Client()
            try:
                socketio_client.connect('http://localhost:8001', wait_timeout=2)
            except Exception:
                pass
        elif not socketio_client.connected:
            try:
                socketio_client.connect('http://localhost:8001', wait_timeout=2)
            except Exception:
                pass
        return socketio_client

def send_session_status(session_hash):
    """Odeslat stav session přes socket.io"""
    try:
        client = get_socketio_client()
        if not client.connected:
            return
        
        session = QuizSession.objects.get(hash=session_hash)
        
        if not session.is_active:
            client.emit('broadcast_session_state', {
                'hash': session_hash,
                'state': 'finished'
            })
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
            data = {
                'hash': session_hash,
                'state': 'question',
                'order': current.order
            }
            client.emit('broadcast_session_state', data)
        else:
            data = {
                'hash': session_hash,
                'state': 'waiting'
            }
            client.emit('broadcast_session_state', data)
    except Exception as e:
        # Pokud socket.io není dostupný, ignorujeme chybu
        pass

def send_answer_update(session_hash, question_order):
    """Odeslat aktualizaci odpovědí přes socket.io"""
    try:
        client = get_socketio_client()
        if not client.connected:
            return
        
        session = QuizSession.objects.get(hash=session_hash)
        qrun = QuestionRun.objects.filter(session=session, order=question_order).first()
        
        if not qrun:
            return
        
        # Statistiky odpovědí
        answer_stats = {}
        for answer in qrun.question.answers.all():
            count = qrun.responses.filter(answer=answer).count()
            answer_stats[str(answer.id)] = count
        
        total_participants = session.participants.count()
        answered_count = qrun.responses.values("participant_id").distinct().count()
        all_answered = total_participants > 0 and answered_count >= total_participants
        
        data = {
            'hash': session_hash,
            'question_order': question_order,
            'answered_count': answered_count,
            'total_participants': total_participants,
            'all_answered': all_answered,
            'answer_stats': answer_stats
        }
        
        client.emit('broadcast_answer_update', data)
    except Exception:
        pass

