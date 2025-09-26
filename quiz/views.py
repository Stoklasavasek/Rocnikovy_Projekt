from django.shortcuts import render, get_object_or_404, redirect
from .models import Quiz, Question, Answer, StudentAnswer
from .forms import QuizForm
from django.contrib.auth.decorators import login_required
from django.contrib import messages

@login_required
def quiz_list(request):
    quizzes = Quiz.objects.filter(created_by=request.user) if request.user.is_authenticated else Quiz.objects.none()
    return render(request, "quiz/quiz_list.html", {"quizzes": quizzes})

@login_required
def quiz_start(request, quiz_id):
    quiz = get_object_or_404(Quiz, id=quiz_id)
    questions = quiz.questions.all()

    if request.method == "POST":
        # Zpracování odpovědí
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
        quiz = Quiz.objects.filter(join_code__iexact=code).first()
        if not quiz:
            messages.error(request, "Kód kvízu je neplatný.")
            return redirect("quiz_join")
        return redirect("quiz_start", quiz_id=quiz.id)
    return render(request, "quiz/join.html")


@login_required
def quiz_create(request):
    if request.method == "POST":
        form = QuizForm(request.POST)
        if form.is_valid():
            quiz = form.save(commit=False)
            quiz.created_by = request.user
            quiz.save()
            messages.success(request, "Kvíz byl vytvořen.")
            return redirect("quiz_list")
    else:
        form = QuizForm()
    return render(request, "quiz/edit.html", {"form": form, "heading": "Vytvořit kvíz"})


@login_required
def quiz_update(request, quiz_id):
    quiz = get_object_or_404(Quiz, id=quiz_id, created_by=request.user)
    if request.method == "POST":
        form = QuizForm(request.POST, instance=quiz)
        if form.is_valid():
            form.save()
            messages.success(request, "Kvíz byl upraven.")
            return redirect("quiz_list")
    else:
        form = QuizForm(instance=quiz)
    return render(request, "quiz/edit.html", {"form": form, "heading": "Upravit kvíz"})


@login_required
def quiz_delete(request, quiz_id):
    quiz = get_object_or_404(Quiz, id=quiz_id, created_by=request.user)
    if request.method == "POST":
        quiz.delete()
        messages.success(request, "Kvíz byl smazán.")
        return redirect("quiz_list")
    return render(request, "quiz/delete.html", {"quiz": quiz})
