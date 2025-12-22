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
    """Zpracuje otázky a odpovědi z POST dat."""
    question_count = 0
    question_index = 0
    
    while True:
        question_text = request.POST.get(f"question_{question_index}_text", "").strip()
        if not question_text:
            break
        
        question_image = request.FILES.get(f"question_{question_index}_image")
        duration = int(request.POST.get(f"question_{question_index}_duration", 20))
        # Validace: minimálně 5 sekund, maximálně 300 sekund (5 minut)
        duration = max(5, min(300, duration))
        question = Question.objects.create(quiz=quiz, text=question_text, image=question_image, duration_seconds=duration)
        question_count += 1
        
        answer_count = 0
        for answer_index in range(10):
            answer_text = request.POST.get(f"question_{question_index}_answer_{answer_index}_text", "").strip()
            if not answer_text:
                continue
            
            is_correct = request.POST.get(f"question_{question_index}_answer_{answer_index}_correct") == "on"
            Answer.objects.create(question=question, text=answer_text, is_correct=is_correct)
            answer_count += 1
        
        if answer_count == 0:
            question.delete()
            question_count -= 1
        
        question_index += 1
    
    return question_count


def _get_question_stats(qrun):
    """Vrátí statistiky odpovědí pro otázku."""
    answer_stats = {}
    participant_responses = {}
    correct_responses = []
    wrong_responses = []
    
    for answer in qrun.question.answers.all():
        count = qrun.responses.filter(answer=answer).count()
        answer_stats[answer.id] = {'answer': answer, 'count': count, 'is_correct': answer.is_correct}
    
    for response in qrun.responses.select_related('participant', 'answer').all():
        response_data = {
            'participant': response.participant,
            'answer': response.answer,
            'is_correct': response.is_correct,
            'answered_at': response.answered_at
        }
        participant_responses[response.participant.id] = response_data
        (correct_responses if response.is_correct else wrong_responses).append(response_data)
    
    responded_ids = set(participant_responses.keys())
    no_answer_responses = [p for p in qrun.session.participants.all() if p.id not in responded_ids]
    
    return answer_stats, participant_responses, correct_responses, wrong_responses, no_answer_responses


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


def _get_question_timing(qrun):
    """Vrátí remaining time a time_over pro otázku."""
    remaining = max(0, int((qrun.ends_at - timezone.now()).total_seconds())) if qrun.ends_at else 0
    time_over = remaining == 0 and qrun.ends_at is not None and timezone.now() >= qrun.ends_at
    return remaining, time_over


def _get_participant_stats(session, qrun=None):
    """Vrátí statistiky účastníků."""
    total_participants = session.participants.count()
    if qrun:
        answered_count = qrun.responses.values("participant_id").distinct().count()
        all_answered = total_participants > 0 and answered_count >= total_participants
        return total_participants, answered_count, all_answered
    return total_participants, 0, False


def _get_or_create_participant(session, user):
    """Vytvoří nebo vrátí participant pro uživatele."""
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
    """Jednodušší režim spuštění kvízu bez „živé" session."""
    quiz = get_object_or_404(Quiz, id=quiz_id)
    questions = quiz.questions.all()
    
    def get_redirect():
        return redirect("quiz_update", quiz_id=quiz.id) if request.user == quiz.created_by else redirect("quiz_list")
    
    if not questions.exists():
        messages.warning(request, "Tento kvíz nemá žádné otázky. Nejdříve přidejte otázky.")
        return get_redirect()
    
    for question in questions:
        if not question.answers.exists():
            messages.warning(request, f"Otázka '{question.text}' nemá žádné odpovědi.")
            return get_redirect()
    
    if request.method == "POST":
        score = 0
        for question in questions:
            if selected_id := request.POST.get(f"question_{question.id}"):
                answer = Answer.objects.get(id=selected_id)
                StudentAnswer.objects.create(student=request.user, question=question, selected_answer=answer)
                if answer.is_correct:
                    score += 1
        return render(request, "quiz/quiz_result.html", {"quiz": quiz, "score": score, "total": questions.count()})
    
    return render(request, "quiz/start.html", {"quiz": quiz, "questions": questions})


@login_required
def join_quiz_by_code(request):
    """Připojení ke kvízu pomocí kódu."""
    if request.method == "POST":
        code = request.POST.get("code", "").strip().upper()
        if session := QuizSession.objects.filter(code__iexact=code, is_active=True).first():
            request.session["session_hash"] = session.hash
            return redirect("session_lobby", hash=session.hash)
        
        if quiz := Quiz.objects.filter(join_code__iexact=code).first():
            return redirect("quiz_start", quiz_id=quiz.id)
        messages.error(request, "Kód je neplatný.")
        return redirect("quiz_join")
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
    """Uložení odpovědi studenta pro právě běžící otázku."""
    session = get_object_or_404(QuizSession, hash=hash, is_active=True)
    qrun = get_object_or_404(QuestionRun, session=session, order=order)
    
    if request.user == session.host:
        messages.error(request, "Učitel nemůže odesílat odpovědi.")
        return redirect("session_question_view", hash=hash, order=order)
    
    participant, _ = _get_or_create_participant(session, request.user)
    
    if request.method == "POST":
        can_answer = qrun.starts_at is not None and (qrun.ends_at is None or timezone.now() <= qrun.ends_at)
        
        if (answer_id := request.POST.get("answer_id")) and can_answer:
            if not Response.objects.filter(question_run=qrun, participant=participant).exists():
                answer = get_object_or_404(Answer, id=answer_id, question=qrun.question)
                Response.objects.create(question_run=qrun, participant=participant, answer=answer, answered_at=timezone.now())
                messages.success(request, "Odpověď uložena.")
                
                total_participants, answered_count, all_answered = _get_participant_stats(session, qrun)
                if all_answered and not qrun.ends_at:
                    qrun.ends_at = timezone.now()
                    qrun.save(update_fields=["ends_at"])
                
                send_answer_update(session.hash, qrun.order)
            else:
                messages.info(request, "Už jsi odpověděl na tuto otázku.")
        elif not can_answer:
            messages.error(request, "Otázka ještě neběží. Počkejte, až učitel spustí otázku." if qrun.starts_at is None else "Čas na odpověď vypršel.")
        
        return redirect("session_question_view", hash=hash, order=order)
    
    return redirect("session_lobby", hash=hash)


@login_required
def session_use_joker(request, hash, order):
    """Použití žolíku studentem během otázky."""
    if request.method != "POST":
        return JsonResponse({"error": "Pouze POST požadavek."}, status=405)
    
    session = get_object_or_404(QuizSession, hash=hash, is_active=True)
    qrun = get_object_or_404(QuestionRun, session=session, order=order)
    
    if request.user == session.host:
        return JsonResponse({"error": "Učitel nemůže používat žolíky."}, status=403)
    
    participant, _ = _get_or_create_participant(session, request.user)
    
    # Kontrola, zda může použít žolík
    if qrun.starts_at is None or (qrun.ends_at and timezone.now() > qrun.ends_at):
        return JsonResponse({"error": "Otázka neběží."}, status=400)
    
    if qrun.responses.filter(participant=participant).exists():
        return JsonResponse({"error": "Už jsi odpověděl na tuto otázku."}, status=400)
    
    max_jokers = session.quiz.jokers_count
    if participant.jokers_used >= max_jokers:
        return JsonResponse({"error": "Už jsi použil všechny žolíky."}, status=400)
    
    # Získání odpovědí
    all_answers = list(qrun.question.answers.all())
    wrong_answers = [a for a in all_answers if not a.is_correct]
    correct_answers = [a for a in all_answers if a.is_correct]
    
    # Smaže 2 špatné odpovědi (nebo všechny, pokud je jich méně)
    removed_count = min(2, len(wrong_answers))
    removed_answers = set(random.sample(wrong_answers, removed_count)) if removed_count > 0 else set()
    
    # 50% šance na polovinu možností (pokud je sudý počet odpovědí)
    if random.random() < 0.5 and len(all_answers) >= 4 and len(all_answers) % 2 == 0:
        target_count = len(all_answers) // 2
        remaining_answers = correct_answers.copy()
        available_wrong = [a for a in wrong_answers if a not in removed_answers]
        if available_wrong:
            needed = max(0, target_count - len(remaining_answers))
            remaining_answers.extend(random.sample(available_wrong, min(needed, len(available_wrong))))
    else:
        remaining_answers = [a for a in all_answers if a not in removed_answers]
    
    # Označit žolík jako použitý
    participant.jokers_used += 1
    participant.save(update_fields=["jokers_used"])
    
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
    """AJAX endpoint pro stav sezení."""
    session = get_object_or_404(QuizSession, hash=hash)
    
    if not session.is_active:
        return JsonResponse({"state": "finished"})
    
    current = _get_current_question_run(session)
    total_participants, _, _ = _get_participant_stats(session)
    
    if current:
        response_data = {"state": "question", "order": current.order, "total_participants": total_participants}
        
        if request.user == session.host:
            answers = current.question.answers.all()
            answer_stats = {str(a.id): current.responses.filter(answer=a).count() for a in answers}
            _, answered_count, all_answered = _get_participant_stats(session, current)
            remaining, _ = _get_question_timing(current)
            
            # Výpočet žebříčku účastníků
            participant_scores = {}
            for resp in Response.objects.filter(
                question_run__session=session,
                question_run__order__lte=current.order
            ).select_related("participant"):
                points = resp.calculate_points()
                participant_scores[resp.participant_id] = participant_scores.get(resp.participant_id, 0) + points
            
            leaderboard = []
            for participant in session.participants.all():
                leaderboard.append({
                    "id": participant.id,
                    "name": participant.display_name,
                    "score": participant_scores.get(participant.id, 0)
                })
            leaderboard.sort(key=lambda x: (x["score"], x["name"]), reverse=True)
            
            response_data.update({
                "answered_count": answered_count,
                "total_participants": total_participants,
                "all_answered": all_answered,
                "answer_stats": answer_stats,
                "correct_answer_ids": [str(a.id) for a in answers if a.is_correct],
                "remaining": remaining,
                "leaderboard": leaderboard
            })
        
        return JsonResponse(response_data)
    
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
    """Finální výsledky sezení."""
    session = get_object_or_404(QuizSession, hash=hash)
    scores = {}
    # Počítáme body podle rychlosti odpovědi
    for resp in Response.objects.filter(question_run__session=session).select_related("participant"):
        points = resp.calculate_points()
        scores[resp.participant_id] = scores.get(resp.participant_id, 0) + points
    
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
    """Export výsledků do CSV."""
    session = get_object_or_404(QuizSession, hash=hash)
    if request.user != session.host:
        return HttpResponse(status=403)
    
    response = HttpResponse(content_type='text/csv')
    response["Content-Disposition"] = f"attachment; filename=results_{session.code}.csv"
    writer = csv.writer(response)
    writer.writerow(["participant", "question", "answer", "is_correct", "response_ms"])
    
    for r in Response.objects.filter(question_run__session=session).select_related("participant", "question_run", "answer", "question_run__question"):
        writer.writerow([
            r.participant.display_name,
            r.question_run.question.text,
            r.answer.text,
            "1" if r.is_correct else "0",
            r.response_ms,
        ])
    
    return response
