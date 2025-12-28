"""
Konfigurace Django aplikace pro kvízy.

Tento modul definuje konfiguraci aplikace 'quiz', která obsahuje
všechny modely, views a logiku pro vytváření a spouštění kvízů.
"""
from django.apps import AppConfig


class QuizConfig(AppConfig):
    """
    Konfigurace aplikace quiz.
    
    Definuje základní nastavení pro Django aplikaci kvízů,
    včetně názvu aplikace a typu primárního klíče.
    """
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'quiz'
