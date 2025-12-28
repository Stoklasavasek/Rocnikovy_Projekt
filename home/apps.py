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
        
        Načte signály pro automatické vytváření uživatelských skupin
        a přiřazování oprávnění.
        """
        from . import signals  # noqa: F401
