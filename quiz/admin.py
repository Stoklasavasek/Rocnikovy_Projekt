"""
Registrace modelů do Django admin rozhraní.

Umožňuje správu kvízů, otázek a odpovědí přes Django admin panel.
"""
from django.contrib import admin
from .models import Quiz, Question, Answer

# Registrace modelů do admin rozhraní
admin.site.register(Quiz)
admin.site.register(Question)
admin.site.register(Answer)
