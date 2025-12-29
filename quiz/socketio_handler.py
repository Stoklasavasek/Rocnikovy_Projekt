"""
Socket.IO handler pro real-time komunikaci v kvízech.

Tento modul zajišťuje komunikaci mezi Django aplikací a samostatným Socket.IO serverem.
Používá se pro odesílání real-time aktualizací (statistiky odpovědí, žebříček, stav sezení)
všem připojeným klientům (učitel i studenti).

Architektura:
- Django aplikace (port 8000) volá funkce z tohoto modulu
- Socket.IO server (port 8001) přijímá zprávy a broadcastuje je klientům
- Klienti (prohlížeče) se připojují k Socket.IO serveru a přijímají aktualizace
"""
import socketio
import threading
import time
from typing import Optional

from django.db.models import Q
from django.utils import timezone

from .models import QuizSession, QuestionRun

# Globální Socket.IO klient pro připojení k serveru
socketio_client: Optional[socketio.Client] = None
_client_lock = threading.Lock()  # Zámek pro thread-safe přístup ke klientovi
SOCKETIO_URL = 'http://localhost:8001'  # URL Socket.IO serveru


def get_socketio_client() -> Optional[socketio.Client]:
    """
    Získat nebo vytvořit socket.io klienta (singleton pattern).
    
    Pokud klient neexistuje nebo není připojen, vytvoří nový a pokusí se připojit.
    Používá thread-safe přístup pomocí zámku pro zajištění konzistence.
    
    Returns:
        socketio.Client objekt nebo None, pokud se připojení nepovede
        
    Note:
        Pokud se připojení nepovede, funkce tiše pokračuje (Socket.IO není kritické
        pro fungování aplikace - používá se jako fallback AJAX polling).
    """
    global socketio_client
    with _client_lock:
        # Vytvoření nového klienta, pokud neexistuje nebo není připojen
        if socketio_client is None or not socketio_client.connected:
            socketio_client = socketio.Client()
            try:
                # Pokus o připojení k Socket.IO serveru
                # wait_timeout=5: čeká max 5 sekund na připojení
                # transports: podporuje polling i websocket
                socketio_client.connect(SOCKETIO_URL, wait_timeout=5, transports=['polling', 'websocket'])
            except Exception:
                # Pokud se připojení nepovede, pokračujeme bez chyby
                # Aplikace může fungovat i bez Socket.IO (použije AJAX polling)
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


def send_answer_update(session_hash: str, question_order: int) -> None:
    """
    Odeslat aktualizaci odpovědí přes socket.io včetně průběžného žebříčku.
    
    Pošle aktuální statistiky odpovědí pro konkrétní otázku všem připojeným klientům.
    Učitel vidí průběžné statistiky v reálném čase včetně průběžného žebříčku účastníků.
    
    Obsahuje:
    - Počty odpovědí pro každou možnost (answer_stats)
    - Odpovědi jednotlivých účastníků (participant_responses)
    - Průběžný žebříček účastníků (leaderboard)
    - Zbývající čas na odpověď (remaining)
    - Informace o tom, zda všichni odpověděli (all_answered)
    
    Args:
        session_hash: Hash sezení pro identifikaci
        question_order: Pořadí otázky v sezení
        
    Note:
        Pokud Socket.IO není dostupný, funkce tiše pokračuje (fallback na AJAX).
    """
    try:
        client = get_socketio_client()
        if not client.connected:
            return
        
        # Optimalizace: načtení sezení s prefetch pro účastníky
        session = QuizSession.objects.prefetch_related("participants").get(hash=session_hash)
        
        # Načtení běhu otázky s optimalizací
        qrun = (
            QuestionRun.objects
            .select_related("question")
            .prefetch_related("question__answers", "responses__answer", "responses__participant")
            .filter(session=session, order=question_order)
            .first()
        )
        if not qrun:
            return
        
        # Počítání statistik odpovědí (optimalizace: načtení všech odpovědí najednou)
        answers = list(qrun.question.answers.all())
        responses = list(qrun.responses.all())
        answer_stats = {str(a.id): sum(1 for r in responses if r.answer_id == a.id) for a in answers}
        
        # Statistiky účastníků
        total_participants = session.participants.count()
        answered_count = len(set(r.participant_id for r in responses))
        all_answered = total_participants > 0 and answered_count >= total_participants
        
        # Shromáždění odpovědí účastníků pro tabulku "Kdo jak odpověděl"
        # Optimalizace: použití slovníku pro rychlejší vyhledávání
        participant_responses_data = {}
        response_by_participant = {r.participant_id: r for r in responses}
        for participant in session.participants.all():
            response = response_by_participant.get(participant.id)
            if response:
                participant_responses_data[str(participant.id)] = {
                    'answer_text': response.answer.text,
                    'is_correct': response.is_correct
                }
            # Účastník ještě neodpověděl - nezahrneme ho do slovníku (bude null v JS)
        
        # Výpočet průběžného žebříčku účastníků (body za všechny dokončené otázky)
        # Optimalizace: jeden dotaz s select_related místo více dotazů
        from .models import Response
        participant_scores = {}
        for resp in Response.objects.filter(
            question_run__session=session,
            question_run__order__lte=question_order
        ).select_related("participant", "answer"):
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
