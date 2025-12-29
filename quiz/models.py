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
    """
    Model reprezentující kvíz.
    
    Kvíz obsahuje otázky, má vlastníka (učitele), unikátní kód pro připojení
    a může mít nastavený počet žolíků (0-3), které mohou studenti použít.
    """
    title = models.CharField(max_length=200, verbose_name="Název kvízu")
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="Vytvořil", related_name="created_quizzes")
    join_code = models.CharField(max_length=8, unique=True, blank=True, verbose_name="Kód pro připojení")
    image = models.ImageField(upload_to="quiz_images/", null=True, blank=True, verbose_name="Obrázek kvízu")
    jokers_count = models.PositiveIntegerField(default=0, help_text="Počet žolíků za celou hru (0-3)", verbose_name="Počet žolíků")

    class Meta:
        verbose_name = "Kvíz"
        verbose_name_plural = "Kvízy"
        ordering = ["-id"]  # Nejnovější první

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        """
        Při prvním uložení automaticky vygeneruje kód pro připojení do kvízu.
        
        Používá se sada znaků bez snadno zaměnitelných písmen/číslic
        (bez I, O, 0, 1) pro lepší čitelnost kódu.
        """
        if not self.join_code:
            self.join_code = get_random_string(
                8,
                allowed_chars="ABCDEFGHJKLMNPQRSTUVWXYZ23456789",
            )
        super().save(*args, **kwargs)


class Question(models.Model):
    """
    Model reprezentující otázku v kvízu.
    
    Každá otázka patří k jednomu kvízu, má text, volitelný obrázek
    a nastavitelný čas na odpověď (5-300 sekund).
    """
    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE, related_name="questions", verbose_name="Kvíz")
    text = models.CharField(max_length=300, verbose_name="Text otázky")
    image = models.ImageField(upload_to="question_images/", null=True, blank=True, verbose_name="Obrázek otázky")
    duration_seconds = models.PositiveIntegerField(default=20, help_text="Čas na odpověď v sekundách (5-300)", verbose_name="Čas na odpověď (s)")

    class Meta:
        verbose_name = "Otázka"
        verbose_name_plural = "Otázky"
        ordering = ["id"]  # Podle pořadí vytvoření

    def __str__(self):
        return self.text[:50] + "..." if len(self.text) > 50 else self.text


class Answer(models.Model):
    """
    Model reprezentující odpověď na otázku.
    
    Každá odpověď patří k jedné otázce, má text a příznak správnosti.
    Otázka může mít více odpovědí, ale obvykle jen jedna je správná.
    """
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name="answers", verbose_name="Otázka")
    text = models.CharField(max_length=200, verbose_name="Text odpovědi")
    is_correct = models.BooleanField(default=False, verbose_name="Správná odpověď")

    class Meta:
        verbose_name = "Odpověď"
        verbose_name_plural = "Odpovědi"
        ordering = ["id"]

    def __str__(self):
        return self.text[:50] + "..." if len(self.text) > 50 else self.text

class StudentAnswer(models.Model):
    """
    Model pro odpovědi studentů v jednoduchém režimu kvízu.
    
    Používá se, když student vyplňuje kvíz samostatně bez živé session.
    Odpovědi se ukládají pro pozdější zobrazení výsledků.
    """
    student = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="Student", related_name="student_answers")
    question = models.ForeignKey(Question, on_delete=models.CASCADE, verbose_name="Otázka")
    selected_answer = models.ForeignKey(Answer, on_delete=models.CASCADE, verbose_name="Vybraná odpověď")
    correct = models.BooleanField(default=False, verbose_name="Správně")

    class Meta:
        verbose_name = "Odpověď studenta"
        verbose_name_plural = "Odpovědi studentů"
        unique_together = ("student", "question")  # Student může odpovědět na otázku jen jednou

    def save(self, *args, **kwargs):
        """
        Při uložení odpovědi vždy znovu spočítá příznak správnosti
        podle navázané odpovědi (Answer.is_correct).
        
        Tím se zajistí konzistence dat i při změně správné odpovědi.
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
    """
    Model reprezentující živé sezení kvízu.
    
    Živé sezení umožňuje učitelovi spustit kvíz v reálném čase,
    studenti se připojují pomocí 6místného kódu a odpovídají na otázky.
    Každé sezení má unikátní hash pro bezpečné URL a kód pro snadné připojení.
    """
    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE, related_name="sessions", verbose_name="Kvíz")
    host = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="Učitel", related_name="hosted_sessions")
    code = models.CharField(max_length=6, unique=True, blank=True, verbose_name="Kód pro připojení", db_index=True)
    hash = models.CharField(max_length=64, unique=True, blank=True, db_index=True, verbose_name="Hash pro URL")
    started_at = models.DateTimeField(null=True, blank=True, verbose_name="Začátek sezení")
    finished_at = models.DateTimeField(null=True, blank=True, verbose_name="Konec sezení")
    is_active = models.BooleanField(default=True, verbose_name="Aktivní", db_index=True)

    class Meta:
        verbose_name = "Sezení kvízu"
        verbose_name_plural = "Sezení kvízů"
        ordering = ["-started_at"]  # Nejnovější první

    def save(self, *args, **kwargs):
        """
        Při vytvoření session automaticky vygeneruje:
         - krátký 6místný kód pro připojení (code),
         - kryptograficky bezpečný 64znakový hash pro URL (hash).
        
        Kód se používá pro snadné připojení studentů,
        hash zajišťuje bezpečnost a unikátnost URL.
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
        return f"Session {self.code} - {self.quiz.title}"


class Participant(models.Model):
    """
    Model reprezentující účastníka živého sezení.
    
    Účastník může být přihlášený uživatel (user) nebo anonymní (jen display_name).
    Sleduje se počet použitých žolíků během sezení.
    """
    session = models.ForeignKey(QuizSession, on_delete=models.CASCADE, related_name="participants", verbose_name="Sezení")
    user = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, verbose_name="Uživatel", related_name="participations")
    display_name = models.CharField(max_length=80, verbose_name="Zobrazované jméno")
    joined_at = models.DateTimeField(default=timezone.now, verbose_name="Připojil se")
    jokers_used = models.PositiveIntegerField(default=0, help_text="Počet použitých žolíků (max podle kvízu)", verbose_name="Použité žolíky")

    class Meta:
        verbose_name = "Účastník"
        verbose_name_plural = "Účastníci"
        ordering = ["joined_at"]  # Podle času připojení
        unique_together = ("session", "display_name")  # V rámci sezení musí být jméno unikátní

    def __str__(self):
        return f"{self.display_name} ({self.session.code})"


class QuestionRun(models.Model):
    """
    Model reprezentující běh konkrétní otázky v živém sezení.
    
    Každá otázka v sezení má svůj QuestionRun, který sleduje,
    kdy byla otázka spuštěna a kdy vypršel čas na odpověď.
    """
    session = models.ForeignKey(QuizSession, on_delete=models.CASCADE, related_name="question_runs", verbose_name="Sezení")
    question = models.ForeignKey(Question, on_delete=models.CASCADE, verbose_name="Otázka")
    order = models.PositiveIntegerField(verbose_name="Pořadí")
    duration_seconds = models.PositiveIntegerField(default=20, verbose_name="Délka (s)")
    starts_at = models.DateTimeField(null=True, blank=True, verbose_name="Začátek", db_index=True)
    ends_at = models.DateTimeField(null=True, blank=True, verbose_name="Konec", db_index=True)

    class Meta:
        verbose_name = "Běh otázky"
        verbose_name_plural = "Běhy otázek"
        unique_together = ("session", "order")  # V rámci sezení musí být pořadí unikátní
        ordering = ["order"]  # Podle pořadí

    def start_now(self):
        """
        Spustí otázku právě teď.
        
        Nastaví starts_at na aktuální čas a spočítá ends_at
        podle duration_seconds. Používá update_fields pro optimalizaci.
        """
        self.starts_at = timezone.now()
        self.ends_at = self.starts_at + timezone.timedelta(
            seconds=self.duration_seconds
        )
        self.save(update_fields=["starts_at", "ends_at"])

    def __str__(self):
        return f"Q{self.order}: {self.question.text[:30]}..."


class Response(models.Model):
    """
    Model reprezentující odpověď účastníka na otázku v živém sezení.
    
    Ukládá se, kterou odpověď účastník vybral, zda byla správná,
    kdy odpověděl a jak rychle (v milisekundách od začátku otázky).
    Body se počítají dynamicky podle rychlosti a správnosti.
    """
    question_run = models.ForeignKey(QuestionRun, on_delete=models.CASCADE, related_name="responses", verbose_name="Běh otázky")
    participant = models.ForeignKey(Participant, on_delete=models.CASCADE, related_name="responses", verbose_name="Účastník")
    answer = models.ForeignKey(Answer, on_delete=models.CASCADE, verbose_name="Odpověď")
    is_correct = models.BooleanField(default=False, verbose_name="Správně", db_index=True)
    answered_at = models.DateTimeField(default=timezone.now, verbose_name="Odpověděl v", db_index=True)
    response_ms = models.PositiveIntegerField(default=0, verbose_name="Čas reakce (ms)", help_text="Čas od začátku otázky v milisekundách")

    class Meta:
        verbose_name = "Odpověď"
        verbose_name_plural = "Odpovědi"
        unique_together = ("question_run", "participant")  # Účastník může odpovědět na otázku jen jednou
        ordering = ["answered_at"]  # Podle času odpovědi

    def calculate_points(self):
        """
        Vypočítá body na základě rychlosti a správnosti odpovědi.
        
        Bodování podle rychlosti (pouze pro správné odpovědi):
        - Špatná odpověď: 0 bodů
        - Správná odpověď:
          - 0-2 sekundy: 900-1000 bodů (lineární pokles: 1000 → 900)
          - 2-15 sekund: 400-900 bodů (lineární pokles: 900 → 400)
          - 15+ sekund: 400 bodů (minimálně)
        
        Returns:
            int: Počet bodů (0-1000)
        """
        if not self.is_correct:
            return 0
        
        response_seconds = self.response_ms / 1000.0
        
        if response_seconds <= 2:
            # 0-2 sekundy: 900-1000 bodů (lineární pokles)
            # Příklad: 0s = 1000, 1s = 950, 2s = 900
            points = 1000 - (response_seconds / 2.0) * 100
        elif response_seconds <= 15:
            # 2-15 sekund: 400-900 bodů (lineární pokles)
            # Příklad: 2s = 900, 8.5s = 650, 15s = 400
            points = 900 - ((response_seconds - 2) / 13.0) * 500
        else:
            # 15+ sekund: 400 bodů (minimálně)
            points = 400
        
        return max(0, int(points))
    
    def save(self, *args, **kwargs):
        """
        Při uložení automaticky dopočítá:
         - příznak správnosti podle navázané odpovědi (Answer.is_correct),
         - čas reakce v milisekundách od začátku otázky (response_ms).
        
        Tím se zajistí konzistence dat i při změně správné odpovědi
        a automatický výpočet rychlosti odpovědi.
        """
        if self.answer_id is not None:
            self.is_correct = self.answer.is_correct
        if self.question_run and self.question_run.starts_at:
            delta = self.answered_at - self.question_run.starts_at
            # Převod rozdílu na celé milisekundy, se spodní hranicí 0
            # (pro případ, že by answered_at bylo před starts_at)
            self.response_ms = max(0, int(delta.total_seconds() * 1000))
        super().save(*args, **kwargs)

    def __str__(self):
        status = "✓" if self.is_correct else "✗"
        return f"{self.participant.display_name} - {status} ({self.response_ms}ms)"
