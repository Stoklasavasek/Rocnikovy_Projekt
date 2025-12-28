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
    """
    Získat nebo vytvořit socket.io klienta.
    Pokud klient není připojen, vytvoří nový.
    """
    global socketio_client
    with _client_lock:
        # Vytvoření nového klienta, pokud neexistuje nebo není připojen
        if socketio_client is None or not socketio_client.connected:
            socketio_client = socketio.Client()
            try:
                # Pokus o připojení k Socket.IO serveru
                socketio_client.connect(SOCKETIO_URL, wait_timeout=5, transports=['polling', 'websocket'])
            except Exception:
                # Pokud se připojení nepovede, pokračujeme bez chyby
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
    """
    Odeslat stav session přes socket.io všem připojeným klientům.
    
    Informuje klienty o aktuálním stavu sezení (čekání, běžící otázka, ukončeno).
    """
    try:
        client = get_socketio_client()
        if not client.connected:
            return
        
        session = QuizSession.objects.get(hash=session_hash)
        # Pokud je sezení ukončeno, pošle informaci o ukončení
        if not session.is_active:
            client.emit('broadcast_session_state', {'hash': session_hash, 'state': 'finished'})
            return
        
        # Zjistí aktuálně běžící otázku
        current = _get_current_question_run(session)
        data = {'hash': session_hash, 'state': 'question' if current else 'waiting'}
        if current:
            data['order'] = current.order  # Přidá pořadové číslo otázky
        client.emit('broadcast_session_state', data)
    except Exception:
        # Při chybě tiše pokračuje (Socket.IO není kritické pro fungování)
        pass


def send_answer_update(session_hash, question_order):
    """
    Odeslat aktualizaci odpovědí přes socket.io včetně průběžného žebříčku.
    
    Pošle aktuální statistiky odpovědí pro konkrétní otázku všem připojeným klientům.
    Učitel vidí průběžné statistiky v reálném čase včetně průběžného žebříčku účastníků.
    """
    try:
        client = get_socketio_client()
        if not client.connected:
            return
        
        session = QuizSession.objects.get(hash=session_hash)
        qrun = QuestionRun.objects.filter(session=session, order=question_order).first()
        if not qrun:
            return
        
        # Počítání statistik odpovědí
        answers = qrun.question.answers.all()
        answer_stats = {str(a.id): qrun.responses.filter(answer=a).count() for a in answers}
        total_participants = session.participants.count()
        answered_count = qrun.responses.values("participant_id").distinct().count()
        all_answered = total_participants > 0 and answered_count >= total_participants
        
        # Shromáždění odpovědí účastníků pro tabulku "Kdo jak odpověděl"
        # Musíme zahrnout všechny účastníky, i ty, kteří ještě neodpověděli
        participant_responses_data = {}
        for participant in session.participants.all():
            response = qrun.responses.filter(participant=participant).first()
            if response:
                participant_responses_data[str(participant.id)] = {
                    'answer_text': response.answer.text,
                    'is_correct': response.is_correct
                }
            # Účastník ještě neodpověděl - nezahrneme ho do slovníku (bude null v JS)
        
        # Výpočet průběžného žebříčku účastníků (body za všechny dokončené otázky)
        from .models import Response
        participant_scores = {}
        for resp in Response.objects.filter(
            question_run__session=session,
            question_run__order__lte=question_order
        ).select_related("participant"):
            points = resp.calculate_points()
            participant_scores[resp.participant_id] = participant_scores.get(resp.participant_id, 0) + points
        
        # Vytvoření seznamu účastníků s body
        leaderboard = []
        for participant in session.participants.all():
            leaderboard.append({
                "id": participant.id,
                "name": participant.display_name,
                "score": participant_scores.get(participant.id, 0)
            })
        # Seřazení podle bodů (sestupně), pak podle jména
        leaderboard.sort(key=lambda x: (x["score"], x["name"]), reverse=True)
        
        # Výpočet zbývajícího času a zda čas vypršel
        remaining = None
        time_over = False
        if qrun.ends_at:
            now = timezone.now()
            if qrun.ends_at > now:
                remaining = int((qrun.ends_at - now).total_seconds())
            else:
                remaining = 0
                time_over = True
        
        # Odeslání aktualizace všem klientům
        client.emit('broadcast_answer_update', {
            'hash': session_hash,
            'question_order': question_order,
            'answered_count': answered_count,
            'total_participants': total_participants,
            'all_answered': all_answered,
            'time_over': time_over,
            'answer_stats': answer_stats,
            'participant_responses': participant_responses_data,
            'leaderboard': leaderboard,
            'remaining': remaining
        })
        # Krátká pauza pro stabilitu připojení
        time.sleep(0.1)
    except Exception:
        # Při chybě tiše pokračuje
        pass
