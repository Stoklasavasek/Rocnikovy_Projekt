from django.shortcuts import render, get_object_or_404, redirect
from .models import Quiz, Question, Answer, StudentAnswer, QuizSession, Participant, QuestionRun, Response
from .forms import QuizForm, QuestionFormSet, AnswerFormSet
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .roles import teacher_required
from django.http import HttpResponse, JsonResponse
from django.db.models import Q
import csv
from django.utils import timezone
def landing(request):
    from quiz.roles import user_is_teacher
    is_teacher = user_is_teacher(request.user) if request.user.is_authenticated else False
    return render(request, "landing.html", {"is_teacher": is_teacher})

@teacher_required
def quiz_list(request):
    from .roles import user_is_teacher
    quizzes = Quiz.objects.filter(created_by=request.user) if request.user.is_authenticated else Quiz.objects.none()
    active_sessions = QuizSession.objects.filter(host=request.user, is_active=True)
    is_teacher = user_is_teacher(request.user)
    return render(request, "quiz/quiz_list.html", {"quizzes": quizzes, "active_sessions": active_sessions, "is_teacher": is_teacher})

@login_required
def quiz_start(request, quiz_id):
    quiz = get_object_or_404(Quiz, id=quiz_id)
    questions = quiz.questions.all()

    if not questions.exists():
        messages.warning(request, "Tento kvíz nemá žádné otázky. Nejdříve přidejte otázky.")
        if request.user == quiz.created_by:
            return redirect("quiz_questions", quiz_id=quiz.id)
        return redirect("quiz_list")

    for question in questions:
        if not question.answers.exists():
            messages.warning(request, f"Otázka '{question.text}' nemá žádné odpovědi.")
            if request.user == quiz.created_by:
                return redirect("quiz_questions", quiz_id=quiz.id)
            return redirect("quiz_list")

    if request.method == "POST":
        score = 0
        for question in questions:
            selected_id = request.POST.get(f"question_{question.id}")
            if selected_id:
                answer = Answer.objects.get(id=selected_id)
                StudentAnswer.objects.create(
                    student=request.user,
                    question=question,
                    selected_answer=answer
                )
                if answer.is_correct:
                    score += 1
        return render(request, "quiz/quiz_result.html", {"quiz": quiz, "score": score, "total": questions.count()})
    
    return render(request, "quiz/start.html", {"quiz": quiz, "questions": questions})


@login_required
def join_quiz_by_code(request):
    if request.method == "POST":
        code = request.POST.get("code", "").strip().upper()
        session = QuizSession.objects.filter(code__iexact=code, is_active=True).first()
        if session:
            request.session["session_hash"] = session.hash
            return redirect("session_lobby", hash=session.hash)
        quiz = Quiz.objects.filter(join_code__iexact=code).first()
        if not quiz:
            messages.error(request, "Kód je neplatný.")
            return redirect("quiz_join")
        return redirect("quiz_start", quiz_id=quiz.id)
    return render(request, "quiz/join.html")


@teacher_required
def quiz_create(request):
    from .roles import user_is_teacher
    is_teacher = user_is_teacher(request.user)
    
    if request.method == "POST":
        # Zpracování vytvoření kvízu s otázkami a odpověďmi najednou
        quiz_title = request.POST.get("quiz_title", "").strip()
        if not quiz_title:
            messages.error(request, "Název kvízu je povinný.")
            return render(request, "quiz/quiz_create_full.html", {"quiz_title": "", "is_teacher": is_teacher})
        
        # Vytvoření kvízu
        quiz = Quiz.objects.create(title=quiz_title, created_by=request.user)
        
        # Zpracování otázek
        question_count = 0
        question_index = 0
        
        while True:
            question_text = request.POST.get(f"question_{question_index}_text", "").strip()
            if not question_text:
                break
            
            question = Question.objects.create(quiz=quiz, text=question_text)
            question_count += 1
            
            # Zpracování odpovědí pro tuto otázku
            answer_count = 0
            for answer_index in range(10):  # Max 10 odpovědí na otázku
                answer_text = request.POST.get(f"question_{question_index}_answer_{answer_index}_text", "").strip()
                if not answer_text:
                    continue
                
                is_correct = request.POST.get(f"question_{question_index}_answer_{answer_index}_correct") == "on"
                Answer.objects.create(question=question, text=answer_text, is_correct=is_correct)
                answer_count += 1
            
            if answer_count == 0:
                # Pokud otázka nemá odpovědi, smažeme ji
                question.delete()
                question_count -= 1
            
            question_index += 1
        
        if question_count > 0:
            messages.success(request, f"Kvíz '{quiz.title}' byl vytvořen s {question_count} otázkami.")
        else:
            messages.warning(request, "Kvíz byl vytvořen, ale nemá žádné otázky.")
        return redirect("quiz_list")
    
    return render(request, "quiz/quiz_create_full.html", {"quiz_title": "", "is_teacher": is_teacher, "quiz": None})


@teacher_required
def quiz_update(request, quiz_id):
    from .roles import user_is_teacher
    quiz = get_object_or_404(Quiz, id=quiz_id, created_by=request.user)
    is_teacher = user_is_teacher(request.user)
    
    if request.method == "POST":
        # Zpracování úpravy kvízu s otázkami a odpověďmi najednou
        quiz_title = request.POST.get("quiz_title", "").strip()
        if not quiz_title:
            messages.error(request, "Název kvízu je povinný.")
            return redirect("quiz_update", quiz_id=quiz.id)
        
        # Aktualizace názvu kvízu
        quiz.title = quiz_title
        quiz.save()
        
        # Smazat všechny existující otázky a odpovědi
        quiz.questions.all().delete()
        
        # Zpracování nových otázek
        question_count = 0
        question_index = 0
        
        while True:
            question_text = request.POST.get(f"question_{question_index}_text", "").strip()
            if not question_text:
                break
            
            question = Question.objects.create(quiz=quiz, text=question_text)
            question_count += 1
            
            # Zpracování odpovědí pro tuto otázku
            answer_count = 0
            for answer_index in range(10):  # Max 10 odpovědí na otázku
                answer_text = request.POST.get(f"question_{question_index}_answer_{answer_index}_text", "").strip()
                if not answer_text:
                    continue
                
                is_correct = request.POST.get(f"question_{question_index}_answer_{answer_index}_correct") == "on"
                Answer.objects.create(question=question, text=answer_text, is_correct=is_correct)
                answer_count += 1
            
            if answer_count == 0:
                # Pokud otázka nemá odpovědi, smažeme ji
                question.delete()
                question_count -= 1
            
            question_index += 1
        
        if question_count > 0:
            messages.success(request, f"Kvíz '{quiz.title}' byl upraven s {question_count} otázkami.")
        else:
            messages.warning(request, "Kvíz byl upraven, ale nemá žádné otázky.")
        return redirect("quiz_list")
    
    # Načtení existujících dat pro editaci
    import json
    from django.utils.safestring import mark_safe
    questions_data = []
    for question in quiz.questions.all().order_by('id'):
        answers_data = []
        for answer in question.answers.all():
            answers_data.append({
                'text': answer.text,
                'is_correct': answer.is_correct
            })
        questions_data.append({
            'text': question.text,
            'answers': answers_data
        })
    
    return render(request, "quiz/quiz_create_full.html", {
        "quiz_title": quiz.title,
        "is_teacher": is_teacher,
        "quiz": quiz,
        "questions_data": mark_safe(json.dumps(questions_data))
    })


@teacher_required
def quiz_questions(request, quiz_id):
    quiz = get_object_or_404(Quiz, id=quiz_id, created_by=request.user)
    if request.method == "POST":
        formset = QuestionFormSet(request.POST, instance=quiz)
        if formset.is_valid():
            formset.save()
            messages.success(request, "Otázky byly uloženy.")
            return redirect("quiz_questions", quiz_id=quiz.id)
    else:
        formset = QuestionFormSet(instance=quiz)
    return render(request, "quiz/questions_edit.html", {"quiz": quiz, "formset": formset})


@teacher_required
def question_answers(request, question_id):
    question = get_object_or_404(Question, id=question_id, quiz__created_by=request.user)
    if request.method == "POST":
        formset = AnswerFormSet(request.POST, instance=question)
        if formset.is_valid():
            formset.save()
            messages.success(request, "Odpovědi byly uloženy.")
            return redirect("quiz_questions", quiz_id=question.quiz.id)
    else:
        formset = AnswerFormSet(instance=question)
    return render(request, "quiz/answers_edit.html", {"question": question, "formset": formset})


@teacher_required
def quiz_delete(request, quiz_id):
    quiz = get_object_or_404(Quiz, id=quiz_id, created_by=request.user)
    if request.method == "POST":
        quiz.delete()
        messages.success(request, "Kvíz byl smazán.")
        return redirect("quiz_list")
    return render(request, "quiz/delete.html", {"quiz": quiz})


@teacher_required
def session_create(request, quiz_id):
    quiz = get_object_or_404(Quiz, id=quiz_id, created_by=request.user)
    session = QuizSession.objects.create(quiz=quiz, host=request.user)
    for index, q in enumerate(quiz.questions.all(), start=1):
        QuestionRun.objects.create(session=session, question=q, order=index)
    return redirect("session_lobby", hash=session.hash)


@login_required
def session_lobby(request, hash):
    session = get_object_or_404(QuizSession, hash=hash, is_active=True)
    is_host = session.host == request.user
    
    participant = None
    if not is_host:
        participant, created = Participant.objects.get_or_create(
            session=session,
            user=request.user,
            defaults={"display_name": request.user.username}
        )
    
    return render(request, "quiz/session_lobby.html", {
        "session": session,
        "is_host": is_host,
        "participant": participant
    })


@teacher_required
def session_start_question(request, hash, order):
    session = get_object_or_404(QuizSession, hash=hash, host=request.user, is_active=True)
    qrun = get_object_or_404(QuestionRun, session=session, order=order)
    qrun.start_now()
    remaining = max(0, int((qrun.ends_at - timezone.now()).total_seconds())) if qrun.ends_at else 0
    is_host = True
    total_participants = session.participants.count()
    answered_count = qrun.responses.values("participant_id").distinct().count()
    all_answered = total_participants > 0 and answered_count >= total_participants
    next_exists = QuestionRun.objects.filter(session=session, order=order + 1).exists()
    return render(
        request,
        "quiz/session_question.html",
        {
            "session": session,
            "qrun": qrun,
            "remaining": remaining,
            "is_host": is_host,
            "total_participants": total_participants,
            "answered_count": answered_count,
            "all_answered": all_answered,
            "next_exists": next_exists,
        },
    )


@login_required
def session_submit_answer(request, hash, order):
    session = get_object_or_404(QuizSession, hash=hash, is_active=True)
    qrun = get_object_or_404(QuestionRun, session=session, order=order)
    if request.user == session.host:
        messages.error(request, "Učitel nemůže odesílat odpovědi.")
        return redirect("session_question_view", hash=hash, order=order)
    participant, _ = Participant.objects.get_or_create(session=session, user=request.user, defaults={"display_name": request.user.username})
    if request.method == "POST":
        answer_id = request.POST.get("answer_id")
        if answer_id and timezone.now() <= (qrun.ends_at or timezone.now()):
            existing = Response.objects.filter(question_run=qrun, participant=participant).exists()
            if not existing:
                answer = get_object_or_404(Answer, id=answer_id, question=qrun.question)
                Response.objects.create(
                    question_run=qrun,
                    participant=participant,
                    answer=answer,
                    answered_at=timezone.now(),
                )
                messages.success(request, "Odpověď uložena.")
                total_participants = session.participants.count()
                answered_count = qrun.responses.values("participant_id").distinct().count()
                if total_participants > 0 and answered_count >= total_participants and not qrun.ends_at:
                    qrun.ends_at = timezone.now()
                    qrun.save(update_fields=["ends_at"])
        return redirect("session_question_view", hash=hash, order=order)
    return redirect("session_lobby", hash=hash)


@login_required
def session_question_view(request, hash, order):
    session = get_object_or_404(QuizSession, hash=hash)
    qrun = get_object_or_404(QuestionRun, session=session, order=order)
    remaining = max(0, int((qrun.ends_at - timezone.now()).total_seconds())) if qrun.ends_at else 0
    is_host = request.user == session.host
    total_participants = session.participants.count()
    answered_count = qrun.responses.values("participant_id").distinct().count()
    all_answered = total_participants > 0 and answered_count >= total_participants
    next_exists = QuestionRun.objects.filter(session=session, order=order + 1).exists()
    has_answered = False
    if not is_host and request.user.is_authenticated:
        participant = Participant.objects.filter(session=session, user=request.user).first()
        if participant:
            has_answered = qrun.responses.filter(participant=participant).exists()
    return render(
        request,
        "quiz/session_question.html",
        {
            "session": session,
            "qrun": qrun,
            "remaining": remaining,
            "is_host": is_host,
            "total_participants": total_participants,
            "answered_count": answered_count,
            "all_answered": all_answered,
            "next_exists": next_exists,
            "has_answered": has_answered,
        },
    )


@login_required
def session_current_question(request, hash):
    session = get_object_or_404(QuizSession, hash=hash, is_active=True)
    now = timezone.now()
    current = (
        session.question_runs
        .filter(starts_at__isnull=False)
        .filter(Q(ends_at__isnull=True) | Q(ends_at__gt=now))
        .order_by("order")
        .last()
    )
    if current:
        return redirect("session_question_view", hash=session.hash, order=current.order)
    messages.info(request, "Zatím není spuštěná žádná otázka.")
    return redirect("session_lobby", hash=session.hash)


@login_required
def session_status(request, hash):
    session = get_object_or_404(QuizSession, hash=hash)
    if not session.is_active:
        return JsonResponse({"state": "finished"})
    now = timezone.now()
    current = (
        session.question_runs
        .filter(starts_at__isnull=False)
        .filter(Q(ends_at__isnull=True) | Q(ends_at__gt=now))
        .order_by("order")
        .last()
    )
    if current:
        return JsonResponse({"state": "question", "order": current.order})
    return JsonResponse({"state": "waiting"})


@teacher_required
def session_finish(request, hash):
    session = get_object_or_404(QuizSession, hash=hash, host=request.user)
    session.is_active = False
    session.finished_at = timezone.now()
    session.save(update_fields=["is_active", "finished_at"])
    return redirect("session_results", hash=hash)


@login_required
def session_results(request, hash):
    session = get_object_or_404(QuizSession, hash=hash)
    is_host = request.user == session.host
    scores = {}
    for resp in Response.objects.filter(question_run__session=session, is_correct=True).select_related("participant"):
        scores[resp.participant_id] = scores.get(resp.participant_id, 0) + 1
    leaderboard = [
        {
            "participant": p,
            "score": scores.get(p.id, 0),
        }
        for p in session.participants.all()
    ]
    leaderboard.sort(key=lambda item: item["score"], reverse=True)
    return render(
        request,
        "quiz/session_results.html",
        {"session": session, "leaderboard": leaderboard, "is_host": is_host},
    )


@teacher_required
def session_results_csv(request, hash):
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
