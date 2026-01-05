"""
Registrace modelů do Django admin rozhraní.

Umožňuje správu kvízů, otázek a odpovědí přes Django admin panel.
Používá se hlavně pro debug a správu dat v produkci.

Note:
    Pro běžnou práci učitelé používají vlastní rozhraní aplikace,
    Django admin slouží spíše pro technickou správu.
"""
from django.contrib import admin
from .models import Quiz, Question, Answer

# Registrace modelů do admin rozhraní
# Modely jsou zaregistrované s výchozími nastaveními
admin.site.register(Quiz)
admin.site.register(Question)
admin.site.register(Answer)
