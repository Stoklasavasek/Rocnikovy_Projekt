"""
Role a oprávnění pro kvízy.

Obsahuje logiku pro rozpoznání role učitele v aplikaci.
Učitelé mohou vytvářet kvízy, spouštět živá sezení a vidět průběžné výsledky.
"""

from django.contrib.auth.models import User

# Název skupiny pro učitele v Django
# Tato skupina se vytváří při migraci nebo ručně v Django adminu
TEACHER_GROUP = "Teacher"


# Kontroluje, jestli je uživatel učitel
def user_is_teacher(user: User) -> bool:
    # Kontrola, zda je přihlášen
    if not user or not user.is_authenticated:
        return False
    
    # True pokud je v skupině TEACHER_GROUP (skupina učitelů) nebo má is_staff
    return user.groups.filter(name=TEACHER_GROUP).exists() or user.is_staff
