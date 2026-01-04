"""
Konfigurace Django aplikace pro domovskou stránku.

Tato aplikace obsahuje základní Wagtail stránky a signály
pro automatické vytváření uživatelských skupin při startu.
"""
from django.apps import AppConfig


class HomeConfig(AppConfig):
    """
    Konfigurace aplikace home.
    
    Při startu aplikace automaticky načte signály pro vytváření
    uživatelských skupin (Admin, Teacher, Student).
    """
    default_auto_field = "django.db.models.BigAutoField"
    name = "home"

    def ready(self):
        """
        Metoda volaná při startu aplikace.
        
        Načte signály pro automatické vytváření uživatelských skupin,
        přiřazování oprávnění a monkey patching pro Wagtail dokumenty.
        
        Důležité:
        - signals.py: Vytváří skupiny Teacher/Student a přiřazuje oprávnění
        - wagtail_signals.py: Opravuje bug v Wagtail search backendu pro dokumenty
        """
        from . import signals  # noqa: F401 - načte signály pro role a oprávnění
        from . import wagtail_signals  # noqa: F401 - načte monkey patching pro dokumenty
