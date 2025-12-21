"""Socket.IO handler pro real-time komunikaci v kvízech."""
import socketio
import threading
import time

from django.db.models import Q
from django.utils import timezone

from .models import QuizSession, QuestionRun

# Klient pro připojení k socket.io serveru
socketio_client = None
_client_lock = threading.Lock()
SOCKETIO_URL = 'http://localhost:8001'


def get_socketio_client():
    """Získat nebo vytvořit socket.io klienta."""
    global socketio_client
    with _client_lock:
        if socketio_client is None or not socketio_client.connected:
            socketio_client = socketio.Client()
            try:
                socketio_client.connect(SOCKETIO_URL, wait_timeout=5, transports=['polling', 'websocket'])
            except Exception:
                pass
        return socketio_client


def _get_current_question_run(session):
    """Vrátí aktuálně běžící otázku v sezení."""
    now = timezone.now()
    return (
        session.question_runs
        .filter(starts_at__isnull=False)
        .filter(Q(ends_at__isnull=True) | Q(ends_at__gt=now))
        .order_by("order")
        .last()
    )


def send_session_status(session_hash):
    """Odeslat stav session přes socket.io."""
    try:
        client = get_socketio_client()
        if not client.connected:
            return
        
        session = QuizSession.objects.get(hash=session_hash)
        if not session.is_active:
            client.emit('broadcast_session_state', {'hash': session_hash, 'state': 'finished'})
            return
        
        current = _get_current_question_run(session)
        data = {'hash': session_hash, 'state': 'question' if current else 'waiting'}
        if current:
            data['order'] = current.order
        client.emit('broadcast_session_state', data)
    except Exception:
        pass


def send_answer_update(session_hash, question_order):
    """Odeslat aktualizaci odpovědí přes socket.io."""
    try:
        client = get_socketio_client()
        if not client.connected:
            return
        
        session = QuizSession.objects.get(hash=session_hash)
        qrun = QuestionRun.objects.filter(session=session, order=question_order).first()
        if not qrun:
            return
        
        answers = qrun.question.answers.all()
        answer_stats = {str(a.id): qrun.responses.filter(answer=a).count() for a in answers}
        total_participants = session.participants.count()
        answered_count = qrun.responses.values("participant_id").distinct().count()
        
        client.emit('broadcast_answer_update', {
            'hash': session_hash,
            'question_order': question_order,
            'answered_count': answered_count,
            'total_participants': total_participants,
            'all_answered': total_participants > 0 and answered_count >= total_participants,
            'answer_stats': answer_stats
        })
        time.sleep(0.1)
    except Exception:
        pass
