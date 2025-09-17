from django.shortcuts import render, get_object_or_404, redirect
from .models import Quiz, Question, Answer, StudentAnswer
from django.contrib.auth.decorators import login_required

@login_required
def quiz_list(request):
    quizzes = Quiz.objects.all()
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
