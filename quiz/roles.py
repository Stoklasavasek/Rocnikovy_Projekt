"""
Role a oprávnění pro kvízy.

Obsahuje logiku pro rozpoznání role učitele v aplikaci.
Učitelé mohou vytvářet kvízy, spouštět živá sezení a vidět průběžné výsledky.
"""

from django.contrib.auth.models import User

# Název skupiny pro učitele v Django
# Tato skupina se vytváří při migraci nebo ručně v Django adminu
TEACHER_GROUP = "Teacher"


def user_is_teacher(user: User) -> bool:
    """
    Zkontroluje, zda je uživatel učitel.
    
    Učitel je buď:
    - člen skupiny "Teacher" (nastaveno v Django adminu), nebo
    - má příznak is_staff (Django admin přístup - automaticky učitel)
    
    Args:
        user: Django User objekt (může být anonymní)
        
    Returns:
        True pokud je uživatel učitel, jinak False
        
    Note:
        Pro anonymní uživatele vždy vrací False (user.is_authenticated je False).
    """
    if not user or not user.is_authenticated:
        return False
    
    # Kontrola členství ve skupině Teacher nebo is_staff
    return user.groups.filter(name=TEACHER_GROUP).exists() or user.is_staff
