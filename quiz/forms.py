from django import forms
from django.forms import inlineformset_factory
from .models import Quiz, Question, Answer


class QuizForm(forms.ModelForm):
    class Meta:
        model = Quiz
        fields = ["title"]
        widgets = {
            "title": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Název kvízu",
            })
        }


class QuestionForm(forms.ModelForm):
    class Meta:
        model = Question
        fields = ["text"]
        widgets = {
            "text": forms.TextInput(attrs={"placeholder": "Text otázky"}),
        }


class AnswerForm(forms.ModelForm):
    class Meta:
        model = Answer
        fields = ["text", "is_correct"]
        widgets = {
            "text": forms.TextInput(attrs={"placeholder": "Text odpovědi"}),
        }


QuestionFormSet = inlineformset_factory(
    Quiz,
    Question,
    form=QuestionForm,
    fields=("text",),
    extra=1,
    can_delete=True,
)

AnswerFormSet = inlineformset_factory(
    Question,
    Answer,
    form=AnswerForm,
    fields=("text", "is_correct"),
    extra=2,
    can_delete=False,
)
