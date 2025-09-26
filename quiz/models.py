from django.db import models
from django.contrib.auth.models import User
from django.utils.crypto import get_random_string
from .models_wagtail import *

class Quiz(models.Model):
    title = models.CharField(max_length=200)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)
    join_code = models.CharField(max_length=8, unique=True, blank=True)

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if not self.join_code:
            # A-Z, 0-9 kód, 8 znaků
            self.join_code = get_random_string(8, allowed_chars="ABCDEFGHJKLMNPQRSTUVWXYZ23456789")
        super().save(*args, **kwargs)

class Question(models.Model):
    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE, related_name="questions")
    text = models.CharField(max_length=300)
    
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
        self.correct = self.selected_answer.is_correct
        super().save(*args, **kwargs)
