"""
Hlavní view funkce pro aplikaci kvízů.

Sem patří:
 - vytváření a správa kvízů učitelem,
 - spouštění „živých“ sezení (QuizSession),
 - zobrazení otázek a zpracování odpovědí studentů,
 - průběžné i finální výsledky kvízu.
"""

import csv
import json
import random

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.safestring import mark_safe

from .models import Answer, Participant, Question, QuestionRun, Quiz, QuizSession, Response, StudentAnswer
from .roles import user_is_teacher
from .socketio_handler import get_socketio_client, send_answer_update, send_session_status


# ===== HELPER FUNKCE =====

def _process_quiz_questions(quiz, request):
    """
    Zpracuje otázky a odpovědi z POST dat při vytváření/úpravě kvízu.
    
    Prochází všechny otázky v POST datech (indexované od 0) a vytváří:
    - Question objekty s textem, obrázkem a časem na odpověď
    - Answer objekty pro každou otázku (max 10 odpovědí na otázku)
    
    Otázky bez odpovědí jsou automaticky smazány.
    
    Returns:
        int: Počet úspěšně vytvořených otázek
    """
    question_count = 0
    question_index = 0
    
    # Procházíme otázky dokud existují v POST datech
    while True:
        question_text = request.POST.get(f"question_{question_index}_text", "").strip()
        if not question_text:
            break  # Konec otázek
        
        # Načtení obrázku otázky (volitelné)
        question_image = request.FILES.get(f"question_{question_index}_image")
        
        # Načtení a validace času na odpověď
        duration = int(request.POST.get(f"question_{question_index}_duration", 20))
        # Validace: minimálně 5 sekund, maximálně 300 sekund (5 minut)
        duration = max(5, min(300, duration))
        
        # Vytvoření otázky
        question = Question.objects.create(quiz=quiz, text=question_text, image=question_image, duration_seconds=duration)
        question_count += 1
        
        # Procházení odpovědí pro tuto otázku (max 10 odpovědí)
        answer_count = 0
        for answer_index in range(10):
            answer_text = request.POST.get(f"question_{question_index}_answer_{answer_index}_text", "").strip()
            if not answer_text:
                continue  # Přeskočit prázdné odpovědi
            
            # Kontrola, zda je odpověď označena jako správná
            is_correct = request.POST.get(f"question_{question_index}_answer_{answer_index}_correct") == "on"
            Answer.objects.create(question=question, text=answer_text, is_correct=is_correct)
            answer_count += 1
        
        # Pokud otázka nemá žádné odpovědi, smažeme ji
        if answer_count == 0:
            question.delete()
            question_count -= 1
        
        question_index += 1
    
    return question_count


def _get_question_stats(qrun):
    """
    Vrátí statistiky odpovědí pro konkrétní otázku v sezení.
    
    Shromažďuje:
    - Počty odpovědí pro každou možnost
    - Odpovědi jednotlivých účastníků
    - Seznam správných a špatných odpovědí
    - Seznam účastníků, kteří ještě neodpověděli
    
    Returns:
        Seznam 5 hodnot:
        - answer_stats: Slovník s počty odpovědí pro každou možnost
        - participant_responses: Slovník s odpověďmi jednotlivých účastníků
        - correct_responses: Seznam správných odpovědí
        - wrong_responses: Seznam špatných odpovědí
        - no_answer_responses: Seznam účastníků, kteří ještě neodpověděli
    """
    answer_stats = {}  # Slovník: answer_id -> {answer, count, is_correct}
    participant_responses = {}  # Slovník: participant_id -> response_data
    correct_responses = []  # Seznam správných odpovědí
    wrong_responses = []  # Seznam špatných odpovědí
    
    # Počítání odpovědí pro každou možnost
    for answer in qrun.question.answers.all():
        count = qrun.responses.filter(answer=answer).count()
        answer_stats[answer.id] = {'answer': answer, 'count': count, 'is_correct': answer.is_correct}
    
    # Shromáždění odpovědí účastníků
    for response in qrun.responses.select_related('participant', 'answer').all():
        response_data = {
            'participant': response.participant,
            'answer': response.answer,
            'is_correct': response.is_correct,
            'answered_at': response.answered_at
        }
        participant_responses[response.participant.id] = response_data
        # Rozdělení na správné a špatné odpovědi
        (correct_responses if response.is_correct else wrong_responses).append(response_data)
    
    # Najít účastníky, kteří ještě neodpověděli
    responded_ids = set(participant_responses.keys())
    no_answer_responses = [p for p in qrun.session.participants.all() if p.id not in responded_ids]
    
    return answer_stats, participant_responses, correct_responses, wrong_responses, no_answer_responses


def _get_current_question_run(session):
    """
    Vrátí aktuálně běžící otázku v sezení.
    
    Otázka je považována za běžící, pokud:
    - Má nastavený starts_at (byla spuštěna)
    - Nemá ends_at NEBO ends_at je v budoucnosti (čas ještě nevypršel)
    
    Returns:
        QuestionRun nebo None, pokud žádná otázka neběží
    """
    now = timezone.now()
    return (
        session.question_runs
        .filter(starts_at__isnull=False)  # Musí být spuštěna
        .filter(Q(ends_at__isnull=True) | Q(ends_at__gt=now))  # Čas ještě nevypršel
        .order_by("order")
        .last()  # Vrátí poslední (nejnovější) běžící otázku
    )


def _get_question_timing(qrun):
    """
    Vypočítá zbývající čas a zda čas vypršel pro otázku.
    
    Returns:
        Seznam 2 hodnot:
        - remaining_seconds: Zbývající sekundy (minimálně 0)
        - time_over: True pokud čas vypršel, jinak False
    """
    # Výpočet zbývajícího času
    remaining = max(0, int((qrun.ends_at - timezone.now()).total_seconds())) if qrun.ends_at else 0
    # Kontrola, zda čas vypršel
    time_over = remaining == 0 and qrun.ends_at is not None and timezone.now() >= qrun.ends_at
    return remaining, time_over


def _get_participant_stats(session, qrun=None):
    """
    Vrátí statistiky účastníků pro sezení nebo konkrétní otázku.
    
    Args:
        session: QuizSession objekt
        qrun: QuestionRun objekt (volitelné, pro statistiky konkrétní otázky)
    
    Returns:
        Seznam 3 hodnot:
        - total_participants: Celkový počet účastníků
        - answered_count: Počet účastníků, kteří odpověděli (pouze pokud qrun je zadán)
        - all_answered: True pokud všichni odpověděli (pouze pokud qrun je zadán)
    """
    total_participants = session.participants.count()
    if qrun:
        # Počet unikátních účastníků, kteří odpověděli na tuto otázku
        answered_count = qrun.responses.values("participant_id").distinct().count()
        # Kontrola, zda všichni odpověděli
        all_answered = total_participants > 0 and answered_count >= total_participants
        return total_participants, answered_count, all_answered
    return total_participants, 0, False


def _get_or_create_participant(session, user):
    """
    Vytvoří nebo vrátí Participant objekt pro uživatele v sezení.
    
    Pokud participant již existuje, vrátí existující.
    Pokud ne, vytvoří nový s display_name = username.
    
    Returns:
        Seznam 2 hodnot:
        - participant: Participant objekt (existující nebo nově vytvořený)
        - created: True pokud byl participant právě vytvořen, jinak False
    """
    return Participant.objects.get_or_create(
        session=session, user=user, defaults={"display_name": user.username}
    )


# ===== VIEW FUNKCE =====

def landing(request):
    """Úvodní obrazovka."""
    is_teacher = user_is_teacher(request.user) if request.user.is_authenticated else False
    return render(request, "landing.html", {"is_teacher": is_teacher})


@login_required
def quiz_list(request):
    """Přehled kvízů aktuálního uživatele a aktivních sezení."""
    quizzes = Quiz.objects.filter(created_by=request.user) if request.user.is_authenticated else Quiz.objects.none()
    active_sessions = QuizSession.objects.filter(host=request.user, is_active=True)
    return render(request, "quiz/quiz_list.html", {
        "quizzes": quizzes,
        "active_sessions": active_sessions,
        "is_teacher": user_is_teacher(request.user)
    })


@login_required
def quiz_start(request, quiz_id):
    """
    Jednodušší režim spuštění kvízu bez „živé" session.
    
    Tento režim umožňuje studentovi vyplnit kvíz samostatně bez učitele.
    Odpovědi se ukládají do StudentAnswer modelu.
    
    GET: Zobrazí formulář s otázkami
    POST: Zpracuje odpovědi a zobrazí výsledky
    """
    quiz = get_object_or_404(Quiz, id=quiz_id)
    questions = quiz.questions.all()
    
    # Pomocná funkce pro přesměrování při chybách
    def get_redirect():
        return redirect("quiz_update", quiz_id=quiz.id) if request.user == quiz.created_by else redirect("quiz_list")
    
    # Validace: kvíz musí mít otázky
    if not questions.exists():
        messages.warning(request, "Tento kvíz nemá žádné otázky. Nejdříve přidejte otázky.")
        return get_redirect()
    
    # Validace: každá otázka musí mít odpovědi
    for question in questions:
        if not question.answers.exists():
            messages.warning(request, f"Otázka '{question.text}' nemá žádné odpovědi.")
            return get_redirect()
    
    # Zpracování odpovědí
    if request.method == "POST":
        score = 0
        for question in questions:
            # Walrus operator: přiřadí a zároveň zkontroluje hodnotu
            if selected_id := request.POST.get(f"question_{question.id}"):
                answer = Answer.objects.get(id=selected_id)
                # Uložení odpovědi studenta
                StudentAnswer.objects.create(student=request.user, question=question, selected_answer=answer)
                # Počítání správných odpovědí
                if answer.is_correct:
                    score += 1
        # Zobrazení výsledků
        return render(request, "quiz/quiz_result.html", {"quiz": quiz, "score": score, "total": questions.count()})
    
    # Zobrazení formuláře s otázkami
    return render(request, "quiz/start.html", {"quiz": quiz, "questions": questions})


@login_required
def join_quiz_by_code(request):
    """
    Připojení ke kvízu pomocí kódu.
    
    Podporuje dva typy kódů:
    1. Kód živé session (6 znaků) - přesměruje do lobby
    2. Kód kvízu (8 znaků) - spustí jednoduchý režim kvízu
    
    GET: Zobrazí formulář pro zadání kódu
    POST: Zpracuje kód a přesměruje na příslušnou stránku
    """
    if request.method == "POST":
        code = request.POST.get("code", "").strip().upper()
        
        # Pokus o připojení k živé session
        if session := QuizSession.objects.filter(code__iexact=code, is_active=True).first():
            # Uložení hashe do session pro pozdější použití
            request.session["session_hash"] = session.hash
            return redirect("session_lobby", hash=session.hash)
        
        # Pokus o připojení k jednoduchému kvízu
        if quiz := Quiz.objects.filter(join_code__iexact=code).first():
            return redirect("quiz_start", quiz_id=quiz.id)
        
        # Kód nebyl nalezen
        messages.error(request, "Kód je neplatný.")
        return redirect("quiz_join")
    
    # Zobrazení formuláře
    return render(request, "quiz/join.html")


@login_required
def quiz_create(request):
    """Vytvoření nového kvízu v jednom formuláři."""
    if request.method == "POST":
        quiz_title = request.POST.get("quiz_title", "").strip()
        if not quiz_title:
            messages.error(request, "Název kvízu je povinný.")
            return render(request, "quiz/quiz_create_full.html", {
                "quiz_title": "",
                "jokers_count": 0,
                "is_teacher": user_is_teacher(request.user)
            })
        
        jokers_count = int(request.POST.get("jokers_count", 0) or 0)
        jokers_count = max(0, min(3, jokers_count))  # Omezit na 0-3
        
        quiz = Quiz.objects.create(title=quiz_title, created_by=request.user, jokers_count=jokers_count)
        question_count = _process_quiz_questions(quiz, request)
        messages.success(request, f"Kvíz '{quiz.title}' byl vytvořen s {question_count} otázkami.") if question_count > 0 else messages.warning(request, "Kvíz byl vytvořen, ale nemá žádné otázky.")
        return redirect("quiz_list")
    
    return render(request, "quiz/quiz_create_full.html", {
        "quiz_title": "",
        "jokers_count": 0,
        "is_teacher": user_is_teacher(request.user),
        "quiz": None
    })


@login_required
def quiz_update(request, quiz_id):
    """Úprava existujícího kvízu."""
    quiz = get_object_or_404(Quiz, id=quiz_id, created_by=request.user)
    
    if request.method == "POST":
        quiz_title = request.POST.get("quiz_title", "").strip()
        if not quiz_title:
            messages.error(request, "Název kvízu je povinný.")
            return redirect("quiz_update", quiz_id=quiz.id)
        
        jokers_count = int(request.POST.get("jokers_count", 0) or 0)
        jokers_count = max(0, min(3, jokers_count))  # Omezit na 0-3
        
        quiz.title = quiz_title
        quiz.jokers_count = jokers_count
        quiz.save()
        quiz.questions.all().delete()
        question_count = _process_quiz_questions(quiz, request)
        messages.success(request, f"Kvíz '{quiz.title}' byl upraven s {question_count} otázkami.") if question_count > 0 else messages.warning(request, "Kvíz byl upraven, ale nemá žádné otázky.")
        return redirect("quiz_list")
    
    questions_data = [{
        'text': q.text,
        'duration': getattr(q, 'duration_seconds', 20),
        'answers': [{'text': a.text, 'is_correct': a.is_correct} for a in q.answers.all()]
    } for q in quiz.questions.all().order_by('id')]
    
    return render(request, "quiz/quiz_create_full.html", {
        "quiz_title": quiz.title,
        "jokers_count": quiz.jokers_count,
        "is_teacher": user_is_teacher(request.user),
        "quiz": quiz,
        "questions_data": mark_safe(json.dumps(questions_data))
    })


@login_required
def quiz_delete(request, quiz_id):
    """Smazání kvízu."""
    quiz = get_object_or_404(Quiz, id=quiz_id, created_by=request.user)
    if request.method == "POST":
        quiz.delete()
        messages.success(request, "Kvíz byl smazán.")
        return redirect("quiz_list")
    return render(request, "quiz/delete.html", {"quiz": quiz})


@login_required
def session_create(request, quiz_id):
    """Vytvoření nového živého sezení."""
    quiz = get_object_or_404(Quiz, id=quiz_id, created_by=request.user)
    session = QuizSession.objects.create(quiz=quiz, host=request.user)
    for index, q in enumerate(quiz.questions.all(), start=1):
        # Vždy použij duration_seconds z Question (má default 20 v modelu)
        # Načteme hodnotu přímo z databáze pomocí values() pro jistotu
        duration = q.duration_seconds if hasattr(q, 'duration_seconds') else 20
        QuestionRun.objects.create(session=session, question=q, order=index, duration_seconds=duration)
    return redirect("session_lobby", hash=session.hash)


@login_required
def session_lobby(request, hash):
    """Lobby pro živé sezení."""
    session = get_object_or_404(QuizSession, hash=hash, is_active=True)
    is_host = session.host == request.user
    participant, _ = _get_or_create_participant(session, request.user) if not is_host else (None, False)
    
    return render(request, "quiz/session_lobby.html", {
        "session": session,
        "is_host": is_host,
        "participant": participant
    })


@login_required
def session_start_question(request, hash, order):
    """Spustí konkrétní otázku v živém sezení (pouze učitel)."""
    session = get_object_or_404(QuizSession, hash=hash, host=request.user, is_active=True)
    qrun = get_object_or_404(QuestionRun, session=session, order=order)
    qrun.start_now()
    qrun.refresh_from_db()
    
    try:
        client = get_socketio_client()
        if client and client.connected:
            client.emit('broadcast_session_state', {'hash': session.hash, 'state': 'question', 'order': order})
    except Exception:
        pass
    
    send_session_status(session.hash)
    # Odeslání počátečních statistik přes Socket.IO
    send_answer_update(session.hash, qrun.order)
    
    remaining, time_over = _get_question_timing(qrun)
    total_participants, answered_count, all_answered = _get_participant_stats(session, qrun)
    
    answer_stats, participant_responses, correct_responses, wrong_responses, no_answer_responses = _get_question_stats(qrun)
    
    return render(request, "quiz/session_question.html", {
        "session": session,
        "qrun": qrun,
        "remaining": remaining,
        "time_over": time_over,
        "is_host": True,
        "total_participants": total_participants,
        "answered_count": answered_count,
        "all_answered": all_answered,
        "next_exists": QuestionRun.objects.filter(session=session, order=order + 1).exists(),
        "answer_stats": answer_stats,
        "participants": session.participants.all(),
        "participant_responses": participant_responses,
        "correct_responses": correct_responses,
        "wrong_responses": wrong_responses,
        "no_answer_responses": no_answer_responses,
    })


@login_required
def session_submit_answer(request, hash, order):
    """
    Uložení odpovědi studenta pro právě běžící otázku.
    
    Validace:
    - Učitel nemůže odpovídat
    - Otázka musí být spuštěna a čas nesmí vypršet
    - Student může odpovědět pouze jednou na otázku
    
    Pokud všichni odpověděli, automaticky ukončí otázku.
    """
    session = get_object_or_404(QuizSession, hash=hash, is_active=True)
    qrun = get_object_or_404(QuestionRun, session=session, order=order)
    
    # Učitel nemůže odpovídat
    if request.user == session.host:
        messages.error(request, "Učitel nemůže odesílat odpovědi.")
        return redirect("session_question_view", hash=hash, order=order)
    
    participant, _ = _get_or_create_participant(session, request.user)
    
    if request.method == "POST":
        # Kontrola, zda může odpovědět (otázka běží a čas nevypršel)
        can_answer = qrun.starts_at is not None and (qrun.ends_at is None or timezone.now() <= qrun.ends_at)
        
        if (answer_id := request.POST.get("answer_id")) and can_answer:
            # Kontrola, zda už neodpověděl
            if not Response.objects.filter(question_run=qrun, participant=participant).exists():
                answer = get_object_or_404(Answer, id=answer_id, question=qrun.question)
                # Vytvoření odpovědi (Response.save() automaticky dopočítá is_correct a response_ms)
                Response.objects.create(question_run=qrun, participant=participant, answer=answer, answered_at=timezone.now())
                messages.success(request, "Odpověď uložena.")
                
                # Kontrola, zda všichni odpověděli - pokud ano, ukončíme otázku
                total_participants, answered_count, all_answered = _get_participant_stats(session, qrun)
                if all_answered and not qrun.ends_at:
                    qrun.ends_at = timezone.now()
                    qrun.save(update_fields=["ends_at"])
                
                # Odeslání aktualizace přes Socket.IO
                send_answer_update(session.hash, qrun.order)
            else:
                messages.info(request, "Už jsi odpověděl na tuto otázku.")
        elif not can_answer:
            # Chybová zpráva podle důvodu
            messages.error(request, "Otázka ještě neběží. Počkejte, až učitel spustí otázku." if qrun.starts_at is None else "Čas na odpověď vypršel.")
        
        return redirect("session_question_view", hash=hash, order=order)
    
    return redirect("session_lobby", hash=hash)


@login_required
def session_use_joker(request, hash, order):
    """
    Použití žolíku studentem během otázky.
    
    Žolík funguje takto:
    1. Smaže 2 náhodné špatné odpovědi
    2. S 50% pravděpodobností (pokud je sudý počet odpovědí >= 4):
       - Zobrazí pouze polovinu možností (správné + některé špatné)
    3. Jinak zobrazí všechny odpovědi kromě 2 smazaných špatných
    
    Vrací JSON s novým seznamem odpovědí a zbývajícím počtem žolíků.
    """
    if request.method != "POST":
        return JsonResponse({"error": "Pouze POST požadavek."}, status=405)
    
    session = get_object_or_404(QuizSession, hash=hash, is_active=True)
    qrun = get_object_or_404(QuestionRun, session=session, order=order)
    
    # Učitel nemůže používat žolíky
    if request.user == session.host:
        return JsonResponse({"error": "Učitel nemůže používat žolíky."}, status=403)
    
    participant, _ = _get_or_create_participant(session, request.user)
    
    # Validace: otázka musí běžet
    if qrun.starts_at is None or (qrun.ends_at and timezone.now() > qrun.ends_at):
        return JsonResponse({"error": "Otázka neběží."}, status=400)
    
    # Validace: student ještě neodpověděl
    if qrun.responses.filter(participant=participant).exists():
        return JsonResponse({"error": "Už jsi odpověděl na tuto otázku."}, status=400)
    
    # Validace: student má ještě žolíky
    max_jokers = session.quiz.jokers_count
    if participant.jokers_used >= max_jokers:
        return JsonResponse({"error": "Už jsi použil všechny žolíky."}, status=400)
    
    # Získání všech odpovědí a jejich rozdělení
    all_answers = list(qrun.question.answers.all())
    wrong_answers = [a for a in all_answers if not a.is_correct]
    correct_answers = [a for a in all_answers if a.is_correct]
    
    # Smazání 2 náhodných špatných odpovědí (nebo všech, pokud je jich méně)
    removed_count = min(2, len(wrong_answers))
    removed_answers = set(random.sample(wrong_answers, removed_count)) if removed_count > 0 else set()
    
    # 50% šance na polovinu možností (pokud je sudý počet odpovědí >= 4)
    if random.random() < 0.5 and len(all_answers) >= 4 and len(all_answers) % 2 == 0:
        # Cíl: polovina všech odpovědí
        target_count = len(all_answers) // 2
        remaining_answers = correct_answers.copy()  # Vždy zahrneme správné odpovědi
        available_wrong = [a for a in wrong_answers if a not in removed_answers]
        if available_wrong:
            # Doplníme špatnými odpověďmi do cílového počtu
            needed = max(0, target_count - len(remaining_answers))
            remaining_answers.extend(random.sample(available_wrong, min(needed, len(available_wrong))))
    else:
        # Zobrazíme všechny odpovědi kromě 2 smazaných špatných
        remaining_answers = [a for a in all_answers if a not in removed_answers]
    
    # Označit žolík jako použitý
    participant.jokers_used += 1
    participant.save(update_fields=["jokers_used"])
    
    # Vrácení výsledku
    return JsonResponse({
        "success": True,
        "remaining_answers": [{"id": a.id, "text": a.text} for a in remaining_answers],
        "jokers_remaining": max_jokers - participant.jokers_used
    })


@login_required
def session_question_view(request, hash, order):
    """Zobrazení stránky otázky."""
    session = get_object_or_404(QuizSession, hash=hash, is_active=True)
    qrun = get_object_or_404(QuestionRun, session=session, order=order)
    
    remaining, time_over = _get_question_timing(qrun)
    is_host = request.user == session.host
    question_started = qrun.starts_at is not None
    total_participants, answered_count, all_answered = _get_participant_stats(session, qrun)
    
    has_answered = False
    participant = None
    current_response = None
    current_points = 0
    total_points = 0
    
    jokers_remaining = 0
    if not is_host and request.user.is_authenticated:
        participant, _ = _get_or_create_participant(session, request.user)
        has_answered = qrun.responses.filter(participant=participant).exists()
        if participant:
            jokers_remaining = max(0, session.quiz.jokers_count - participant.jokers_used)
        
        # Získání aktuální odpovědi a bodů
        if has_answered:
            current_response = qrun.responses.filter(participant=participant).first()
            if current_response:
                current_points = current_response.calculate_points()
        
        # Výpočet celkových bodů za všechny dokončené otázky (včetně aktuální, pokud už odpověděl)
        completed_responses = Response.objects.filter(
            question_run__session=session,
            question_run__order__lte=order,
            participant=participant
        )
        for resp in completed_responses:
            total_points += resp.calculate_points()
    
    answer_stats, participant_responses, correct_responses, wrong_responses, no_answer_responses = (
        _get_question_stats(qrun) if is_host else ({}, {}, [], [], [])
    )
    
    # Výpočet bodů pro všechny účastníky (pro učitele)
    participant_leaderboard = []
    if is_host:
        participant_scores = {}
        # Počítáme body za všechny dokončené otázky (včetně aktuální)
        for resp in Response.objects.filter(
            question_run__session=session,
            question_run__order__lte=order
        ).select_related("participant"):
            points = resp.calculate_points()
            participant_scores[resp.participant_id] = participant_scores.get(resp.participant_id, 0) + points
        
        # Vytvoříme seznam účastníků s body (i když mají 0 bodů)
        for participant in session.participants.all():
            participant_leaderboard.append({
                "participant": participant,
                "score": participant_scores.get(participant.id, 0)
            })
        
        # Seřadíme podle bodů (sestupně), pak podle jména pro konzistenci
        participant_leaderboard.sort(key=lambda x: (x["score"], x["participant"].display_name), reverse=True)
    
    return render(request, "quiz/session_question.html", {
        "session": session,
        "qrun": qrun,
        "remaining": remaining,
        "time_over": time_over,
        "is_host": is_host,
        "question_started": question_started,
        "total_participants": total_participants,
        "answered_count": answered_count,
        "all_answered": all_answered,
        "next_exists": QuestionRun.objects.filter(session=session, order=order + 1).exists(),
        "has_answered": has_answered,
        "answer_stats": answer_stats,
        "participants": session.participants.all(),
        "current_response": current_response,
        "current_points": current_points,
        "total_points": total_points,
        "participant_responses": participant_responses,
        "correct_responses": correct_responses,
        "wrong_responses": wrong_responses,
        "no_answer_responses": no_answer_responses,
        "participant_leaderboard": participant_leaderboard,
        "jokers_remaining": jokers_remaining,
    })


@login_required
def session_current_question(request, hash):
    """Přesměrování na aktuálně běžící otázku."""
    session = get_object_or_404(QuizSession, hash=hash, is_active=True)
    current = _get_current_question_run(session)
    
    if current:
        return redirect("session_question_view", hash=session.hash, order=current.order)
    
    messages.info(request, "Zatím není spuštěná žádná otázka.")
    return redirect("session_lobby", hash=session.hash)


@login_required
def session_status(request, hash):
    """
    AJAX endpoint pro stav sezení - používá se pro real-time aktualizace.
    
    Vrací JSON s aktuálním stavem:
    - "finished": Sezení je ukončeno
    - "waiting": Čeká se na spuštění otázky
    - "question": Běží otázka (s detaily pro učitele)
    
    Pro učitele navíc vrací:
    - Statistiky odpovědí
    - Průběžný žebříček účastníků
    - Informace o zbývajícím čase
    """
    session = get_object_or_404(QuizSession, hash=hash)
    
    # Sezení je ukončeno
    if not session.is_active:
        return JsonResponse({"state": "finished"})
    
    current = _get_current_question_run(session)
    total_participants, _, _ = _get_participant_stats(session)
    
    if current:
        # Běží otázka
        response_data = {"state": "question", "order": current.order, "total_participants": total_participants}
        
        # Pro učitele přidáme detailní statistiky
        if request.user == session.host:
            answers = current.question.answers.all()
            # Počty odpovědí pro každou možnost
            answer_stats = {str(a.id): current.responses.filter(answer=a).count() for a in answers}
            _, answered_count, all_answered = _get_participant_stats(session, current)
            remaining, _ = _get_question_timing(current)
            
            # Výpočet průběžného žebříčku účastníků (body za všechny dokončené otázky)
            participant_scores = {}
            for resp in Response.objects.filter(
                question_run__session=session,
                question_run__order__lte=current.order
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
            
            # Shromáždění odpovědí účastníků pro tabulku "Kdo jak odpověděl"
            participant_responses_data = {}
            for participant in session.participants.all():
                response = current.responses.filter(participant=participant).first()
                if response:
                    participant_responses_data[str(participant.id)] = {
                        'answer_text': response.answer.text,
                        'is_correct': response.is_correct
                    }
            
            remaining, time_over = _get_question_timing(current)
            
            # Přidání detailních statistik do odpovědi
            response_data.update({
                "answered_count": answered_count,
                "total_participants": total_participants,
                "all_answered": all_answered,
                "time_over": time_over,
                "answer_stats": answer_stats,
                "participant_responses": participant_responses_data,
                "correct_answer_ids": [str(a.id) for a in answers if a.is_correct],
                "remaining": remaining,
                "leaderboard": leaderboard
            })
        
        return JsonResponse(response_data)
    
    # Čeká se na spuštění otázky
    return JsonResponse({"state": "waiting", "total_participants": total_participants})


@login_required
def session_finish(request, hash):
    """Ukončení živého sezení."""
    session = get_object_or_404(QuizSession, hash=hash, host=request.user)
    session.is_active = False
    session.finished_at = timezone.now()
    session.save(update_fields=["is_active", "finished_at"])
    
    send_session_status(session.hash)
    
    return redirect("session_results", hash=hash)


@login_required
def session_results(request, hash):
    """
    Finální výsledky sezení - zobrazí žebříček všech účastníků.
    
    Body se počítají podle rychlosti a správnosti odpovědi pomocí
    Response.calculate_points() metody.
    
    Žebříček je seřazen podle celkového počtu bodů (sestupně).
    """
    session = get_object_or_404(QuizSession, hash=hash)
    scores = {}
    
    # Počítáme body podle rychlosti odpovědi pro všechny odpovědi v sezení
    for resp in Response.objects.filter(question_run__session=session).select_related("participant"):
        points = resp.calculate_points()
        scores[resp.participant_id] = scores.get(resp.participant_id, 0) + points
    
    # Vytvoření a seřazení žebříčku
    leaderboard = sorted(
        [{"participant": p, "score": scores.get(p.id, 0)} for p in session.participants.all()],
        key=lambda x: x["score"], reverse=True
    )
    
    return render(request, "quiz/session_results.html", {
        "session": session,
        "leaderboard": leaderboard,
        "is_host": request.user == session.host
    })


@login_required
def session_results_csv(request, hash):
    """
    Export výsledků sezení do CSV souboru.
    
    Pouze host (učitel) může stáhnout výsledky.
    
    CSV obsahuje:
    - Jméno účastníka
    - Text otázky
    - Text odpovědi
    - Zda byla odpověď správná (1/0)
    - Čas odpovědi v milisekundách
    """
    session = get_object_or_404(QuizSession, hash=hash)
    # Pouze host může stáhnout výsledky
    if request.user != session.host:
        return HttpResponse(status=403)
    
    # Nastavení HTTP hlaviček pro stažení CSV
    response = HttpResponse(content_type='text/csv')
    response["Content-Disposition"] = f"attachment; filename=results_{session.code}.csv"
    writer = csv.writer(response)
    
    # Hlavička CSV
    writer.writerow(["participant", "question", "answer", "is_correct", "response_ms"])
    
    # Zápis všech odpovědí
    for r in Response.objects.filter(question_run__session=session).select_related("participant", "question_run", "answer", "question_run__question"):
        writer.writerow([
            r.participant.display_name,
            r.question_run.question.text,
            r.answer.text,
            "1" if r.is_correct else "0",
            r.response_ms,
        ])
    
    return response
