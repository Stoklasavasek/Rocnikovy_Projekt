"""
Modely pro kvízy a „živá“ sezení.

Obsahuje:
 - strukturu kvízu (Quiz, Question, Answer),
 - odpovědi studentů v jednoduchém režimu (StudentAnswer),
 - živé sezení s unikátním kódem a hashem (QuizSession, Participant),
 - běh jednotlivých otázek v sezení (QuestionRun),
 - konkrétní odpovědi v rámci běhu otázky (Response).
"""

import hashlib
import secrets

from django.conf import settings
from django.contrib.auth.models import User
from django.db import models
from django.utils import timezone
from django.utils.crypto import get_random_string


class Quiz(models.Model):
    title = models.CharField(max_length=200)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)
    join_code = models.CharField(max_length=8, unique=True, blank=True)
    image = models.ImageField(upload_to="quiz_images/", null=True, blank=True)

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        """
        Při prvním uložení automaticky vygeneruje kód pro připojení do kvízu.

        Používá se sada znaků bez snadno zaměnitelných písmen/číslic.
        """
        if not self.join_code:
            self.join_code = get_random_string(
                8,
                allowed_chars="ABCDEFGHJKLMNPQRSTUVWXYZ23456789",
            )
        super().save(*args, **kwargs)


class Question(models.Model):
    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE, related_name="questions")
    text = models.CharField(max_length=300)
    image = models.ImageField(upload_to="question_images/", null=True, blank=True)
    duration_seconds = models.PositiveIntegerField(default=20, help_text="Čas na odpověď v sekundách")

    def __str__(self):
        return self.text

class Answer(models.Model):
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name="answers")
    text = models.CharField(max_length=200)
    is_correct = models.BooleanField(default=False)

    def __str__(self):
        return self.text

class StudentAnswer(models.Model):
    student = models.ForeignKey(User, on_delete=models.CASCADE)
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    selected_answer = models.ForeignKey(Answer, on_delete=models.CASCADE)
    correct = models.BooleanField(default=False)

    def save(self, *args, **kwargs):
        """
        Při uložení odpovědi vždy znovu spočítá příznak správnosti
        podle navázané odpovědi (Answer.is_correct).
        """
        self.correct = self.selected_answer.is_correct
        super().save(*args, **kwargs)


def generate_session_hash():
    """
    Vygeneruje kryptograficky bezpečný hash pro URL sezení.

    Kombinuje náhodný token, SECRET_KEY a aktuální čas, a z výsledku
    SHA-256 bere prvních 64 znaků hexadecimální reprezentace.
    """
    random_token = secrets.token_urlsafe(32)
    secret_key = getattr(settings, "SECRET_KEY", "default-secret-key")
    combined = f"{random_token}{secret_key}{timezone.now().isoformat()}"
    return hashlib.sha256(combined.encode()).hexdigest()[:64]


class QuizSession(models.Model):
    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE, related_name="sessions")
    host = models.ForeignKey(User, on_delete=models.CASCADE)
    code = models.CharField(max_length=6, unique=True, blank=True)
    hash = models.CharField(max_length=64, unique=True, blank=True, db_index=True)
    started_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)

    def save(self, *args, **kwargs):
        """
        Při vytvoření session doplní vždy:
         - krátký kód pro připojení (code),
         - kryptograficky bezpečný hash pro URL (hash).
        """
        if not self.code:
            self.code = get_random_string(
                6,
                allowed_chars="ABCDEFGHJKLMNPQRSTUVWXYZ23456789",
            )
        if not self.hash:
            self.hash = generate_session_hash()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Session {self.code} for {self.quiz}"


class Participant(models.Model):
    session = models.ForeignKey(QuizSession, on_delete=models.CASCADE, related_name="participants")
    user = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL)
    display_name = models.CharField(max_length=80)
    joined_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return self.display_name


class QuestionRun(models.Model):
    session = models.ForeignKey(QuizSession, on_delete=models.CASCADE, related_name="question_runs")
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    order = models.PositiveIntegerField()
    duration_seconds = models.PositiveIntegerField(default=20)
    starts_at = models.DateTimeField(null=True, blank=True)
    ends_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ("session", "order")

    def start_now(self):
        """
        Spustí otázku právě teď.

        Nastaví starts_at na aktuální čas a spočítá ends_at podle duration_seconds.
        """
        self.starts_at = timezone.now()
        self.ends_at = self.starts_at + timezone.timedelta(
            seconds=self.duration_seconds
        )
        self.save(update_fields=["starts_at", "ends_at"])


class Response(models.Model):
    question_run = models.ForeignKey(QuestionRun, on_delete=models.CASCADE, related_name="responses")
    participant = models.ForeignKey(Participant, on_delete=models.CASCADE, related_name="responses")
    answer = models.ForeignKey(Answer, on_delete=models.CASCADE)
    is_correct = models.BooleanField(default=False)
    answered_at = models.DateTimeField(default=timezone.now)
    response_ms = models.PositiveIntegerField(default=0)

    def calculate_points(self):
        """
        Vypočítá body na základě rychlosti a správnosti odpovědi.
        
        Vzorec:
        - Špatná odpověď: 0 bodů
        - Správná odpověď:
          - 0-2 sekundy: 900-1000 bodů
          - 2-15 sekund: 400-900 bodů
          - 15+ sekund: 400 bodů (minimálně)
        """
        if not self.is_correct:
            return 0
        
        response_seconds = self.response_ms / 1000.0
        
        if response_seconds <= 2:
            # 0-2 sekundy: 900-1000 bodů (lineární pokles)
            points = 1000 - (response_seconds / 2.0) * 100
        elif response_seconds <= 15:
            # 2-15 sekund: 400-900 bodů (lineární pokles)
            points = 900 - ((response_seconds - 2) / 13.0) * 500
        else:
            # 15+ sekund: 400 bodů (minimálně)
            points = 400
        
        return max(0, int(points))
    
    def save(self, *args, **kwargs):
        """
        Při uložení vždy dopočítá:
         - příznak správnosti podle navázané odpovědi,
         - čas reakce v milisekundách od začátku otázky (response_ms).
        """
        if self.answer_id is not None:
            self.is_correct = self.answer.is_correct
        if self.question_run and self.question_run.starts_at:
            delta = self.answered_at - self.question_run.starts_at
            # Převod rozdílu na celé milisekundy, se spodní hranicí 0.
            self.response_ms = max(0, int(delta.total_seconds() * 1000))
        super().save(*args, **kwargs)
