"""
Samostatný Socket.IO server pro real-time komunikaci v kvízech.

Tento server běží na portu 8001 a zajišťuje real-time komunikaci mezi:
- Django aplikací (port 8000) - odesílá aktualizace
- Klienty (prohlížeče) - přijímají aktualizace

Architektura:
1. Django aplikace volá funkce z quiz/socketio_handler.py
2. Tyto funkce se připojí k tomuto serveru a odešlou zprávy
3. Server broadcastuje zprávy všem klientům v příslušné "room" (session)
4. Klienti přijímají zprávy a aktualizují UI v reálném čase

Používá eventlet pro asynchronní zpracování a periodické aktualizace.
"""
import os
import time
from typing import Dict, Any, Optional

import django
import eventlet
import socketio
from django.db.models import Q
from django.utils import timezone

from quiz.models import QuizSession, QuestionRun, Response

# Nastavení Django pro přístup k databázi
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "kahootapp.settings.dev")
django.setup()

# Vytvoření Socket.IO serveru s CORS povoleným pro všechny originy
# async_mode="eventlet" umožňuje asynchronní zpracování
sio = socketio.Server(cors_allowed_origins="*", async_mode="eventlet")
app = socketio.WSGIApp(sio)


def get_room_name(session_hash: str) -> str:
    """
    Vrátí název room (místnosti) pro session.
    
    Socket.IO používá "rooms" pro seskupení klientů - všichni klienti
    v jedné room dostávají stejné zprávy. Každé sezení má svou vlastní room.
    
    Args:
        session_hash: Hash sezení pro identifikaci
        
    Returns:
        Název room ve formátu "session_{hash}"
    """
    return f"session_{session_hash}"


def get_current_question_run(session: QuizSession) -> Optional[QuestionRun]:
    """
    Vrátí aktuálně běžící otázku v sezení.
    
    Otázka je považována za běžící, pokud:
    - Má nastavený starts_at (byla spuštěna)
    - Nemá ends_at NEBO ends_at je v budoucnosti (čas ještě nevypršel)
    
    Args:
        session: QuizSession objekt
        
    Returns:
        QuestionRun objekt nebo None, pokud žádná otázka neběží
    """
    now = timezone.now()
    return (
        session.question_runs
        .filter(starts_at__isnull=False)  # Musí být spuštěna
        .filter(Q(ends_at__isnull=True) | Q(ends_at__gt=now))  # Čas ještě nevypršel
        .order_by("order")  # Seřazeno podle pořadí
        .last()  # Vrátí poslední (nejnovější) běžící otázku
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
            # Při čekání pošleme také seznam účastníků pro aktualizaci
            participants_list = [{"id": p.id, "name": p.display_name} for p in session.participants.all()]
            sio.emit('session_state', {
                'state': 'waiting',
                'total_participants': session.participants.count(),
                'participants': participants_list
            }, room=room_name)
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
    """Broadcast aktualizaci odpovědí z Django včetně průběžného žebříčku a odpovědí účastníků."""
    session_hash = data.get('hash')
    if session_hash:
        sio.emit('answer_update', {
            'question_order': data.get('question_order'),
            'answered_count': data.get('answered_count'),
            'total_participants': data.get('total_participants'),
            'all_answered': data.get('all_answered'),
            'time_over': data.get('time_over'),
            'answer_stats': data.get('answer_stats'),
            'participant_responses': data.get('participant_responses'),
            'leaderboard': data.get('leaderboard'),
            'remaining': data.get('remaining')
        }, room=get_room_name(session_hash))


def _calculate_question_stats(qrun, session):
    """Vypočítá statistiky pro otázku."""
    answers = qrun.question.answers.all()
    answer_stats = {str(a.id): qrun.responses.filter(answer=a).count() for a in answers}
    total_participants = session.participants.count()
    answered_count = qrun.responses.values("participant_id").distinct().count()
    all_answered = total_participants > 0 and answered_count >= total_participants
    
    participant_responses_data = {}
    for participant in session.participants.all():
        response = qrun.responses.filter(participant=participant).first()
        if response:
            participant_responses_data[str(participant.id)] = {
                'answer_text': response.answer.text,
                'is_correct': response.is_correct
            }
    
    return answer_stats, total_participants, answered_count, all_answered, participant_responses_data


def _calculate_leaderboard(session, question_order):
    """Vypočítá průběžný žebříček účastníků."""
    participant_scores = {}
    for resp in Response.objects.filter(
        question_run__session=session,
        question_run__order__lte=question_order
    ).select_related("participant"):
        points = resp.calculate_points()
        participant_scores[resp.participant_id] = participant_scores.get(resp.participant_id, 0) + points
    
    leaderboard = [
        {
            "id": p.id,
            "name": p.display_name,
            "score": participant_scores.get(p.id, 0)
        }
        for p in session.participants.all()
    ]
    leaderboard.sort(key=lambda x: (x["score"], x["name"]), reverse=True)
    return leaderboard


def send_periodic_updates() -> None:
    """
    Periodicky posílá aktualizace pro všechny aktivní otázky.
    
    Tato funkce běží v background threadu a každou sekundu:
    1. Najde všechna aktivní sezení
    2. Pro každé sezení najde aktuálně běžící otázku
    3. Vypočítá statistiky a žebříček
    4. Odešle aktualizace všem klientům v room
    
    Zajišťuje, že učitel vidí statistiky v reálném čase i bez nových odpovědí
    (např. zbývající čas, průběžný žebříček).
    
    Note:
        Používá eventlet.sleep(1) pro asynchronní čekání (neblokuje ostatní operace).
        Při chybě tiše pokračuje, aby neohrozila běh serveru.
    """
    while True:
        try:
            now = timezone.now()
            # Optimalizace: načtení pouze aktivních sezení s prefetch
            for session in QuizSession.objects.filter(is_active=True).prefetch_related("participants", "question_runs__question"):
                qrun = get_current_question_run(session)
                if not (qrun and qrun.starts_at):
                    continue  # Žádná otázka neběží, přeskočit
                
                # Výpočet statistik pro aktuální otázku
                answer_stats, total_participants, answered_count, all_answered, participant_responses_data = (
                    _calculate_question_stats(qrun, session)
                )
                # Výpočet průběžného žebříčku
                leaderboard = _calculate_leaderboard(session, qrun.order)
                
                # Výpočet zbývajícího času
                remaining = None
                time_over = False
                if qrun.ends_at:
                    remaining = max(0, int((qrun.ends_at - now).total_seconds())) if qrun.ends_at > now else 0
                    time_over = remaining == 0
                
                # Odeslání aktualizace všem klientům v room
                sio.emit('answer_update', {
                    'question_order': qrun.order,
                    'answered_count': answered_count,
                    'total_participants': total_participants,
                    'all_answered': all_answered,
                    'time_over': time_over,
                    'answer_stats': answer_stats,
                    'participant_responses': participant_responses_data,
                    'leaderboard': leaderboard,
                    'remaining': remaining
                }, room=get_room_name(session.hash))
        except Exception:
            # Při chybě tiše pokračujeme, aby neohrozila běh serveru
            pass
        
        # Asynchronní čekání 1 sekundu (neblokuje ostatní operace)
        eventlet.sleep(1)


if __name__ == '__main__':
    # Spuštění background threadu pro periodické aktualizace
    eventlet.spawn(send_periodic_updates)
    # Spuštění Socket.IO serveru
    eventlet.wsgi.server(eventlet.listen(('0.0.0.0', 8001)), app)
