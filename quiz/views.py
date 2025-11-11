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
    return render(request, "landing.html")

@teacher_required
def quiz_list(request):
    quizzes = Quiz.objects.filter(created_by=request.user) if request.user.is_authenticated else Quiz.objects.none()
    active_sessions = QuizSession.objects.filter(host=request.user, is_active=True)
    return render(request, "quiz/quiz_list.html", {"quizzes": quizzes, "active_sessions": active_sessions})

@login_required
def quiz_start(request, quiz_id):
    quiz = get_object_or_404(Quiz, id=quiz_id)
    questions = quiz.questions.all()

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
            request.session["session_code"] = session.code
            return redirect("session_lobby", code=session.code)
        quiz = Quiz.objects.filter(join_code__iexact=code).first()
        if not quiz:
            messages.error(request, "Kód je neplatný.")
            return redirect("quiz_join")
        return redirect("quiz_start", quiz_id=quiz.id)
    return render(request, "quiz/join.html")


@teacher_required
def quiz_create(request):
    if request.method == "POST":
        form = QuizForm(request.POST)
        if form.is_valid():
            quiz = form.save(commit=False)
            quiz.created_by = request.user
            quiz.save()
            messages.success(request, "Kvíz byl vytvořen. Přidejte otázky.")
            return redirect("quiz_questions", quiz_id=quiz.id)
    else:
        form = QuizForm()
    return render(request, "quiz/edit.html", {"form": form, "heading": "Vytvořit kvíz"})


@teacher_required
def quiz_update(request, quiz_id):
    quiz = get_object_or_404(Quiz, id=quiz_id, created_by=request.user)
    if request.method == "POST":
        form = QuizForm(request.POST, instance=quiz)
        if form.is_valid():
            form.save()
            messages.success(request, "Kvíz byl upraven.")
            return redirect("quiz_questions", quiz_id=quiz.id)
    else:
        form = QuizForm(instance=quiz)
    return render(request, "quiz/edit.html", {"form": form, "heading": "Upravit kvíz"})


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
    return redirect("session_lobby", code=session.code)


@login_required
def session_lobby(request, code):
    session = get_object_or_404(QuizSession, code__iexact=code, is_active=True)
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
def session_start_question(request, code, order):
    session = get_object_or_404(QuizSession, code__iexact=code, host=request.user, is_active=True)
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
def session_submit_answer(request, code, order):
    session = get_object_or_404(QuizSession, code__iexact=code, is_active=True)
    qrun = get_object_or_404(QuestionRun, session=session, order=order)
    if request.user == session.host:
        messages.error(request, "Učitel nemůže odesílat odpovědi.")
        return redirect("session_question_view", code=code, order=order)
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
        return redirect("session_question_view", code=code, order=order)
    return redirect("session_lobby", code=code)


@login_required
def session_question_view(request, code, order):
    session = get_object_or_404(QuizSession, code__iexact=code)
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
def session_current_question(request, code):
    session = get_object_or_404(QuizSession, code__iexact=code, is_active=True)
    now = timezone.now()
    current = (
        session.question_runs
        .filter(starts_at__isnull=False)
        .filter(Q(ends_at__isnull=True) | Q(ends_at__gt=now))
        .order_by("order")
        .last()
    )
    if current:
        return redirect("session_question_view", code=session.code, order=current.order)
    messages.info(request, "Zatím není spuštěná žádná otázka.")
    return redirect("session_lobby", code=session.code)


@login_required
def session_status(request, code):
    session = get_object_or_404(QuizSession, code__iexact=code)
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
def session_finish(request, code):
    session = get_object_or_404(QuizSession, code__iexact=code, host=request.user)
    session.is_active = False
    session.finished_at = timezone.now()
    session.save(update_fields=["is_active", "finished_at"])
    return redirect("session_results", code=code)


@login_required
def session_results(request, code):
    session = get_object_or_404(QuizSession, code__iexact=code)
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
def session_results_csv(request, code):
    session = get_object_or_404(QuizSession, code__iexact=code)
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
