"""
Role a oprávnění pro kvízy.

Obsahuje logiku pro rozpoznání role učitele v aplikaci.
"""

# Název skupiny pro učitele v Django
TEACHER_GROUP = "Teacher"


def user_is_teacher(user) -> bool:
    """
    Zkontroluje, zda je uživatel učitel.
    
    Učitel je buď:
    - člen skupiny "Teacher", nebo
    - má příznak is_staff (Django admin přístup)
    """
    return user.is_authenticated and (user.groups.filter(name=TEACHER_GROUP).exists() or user.is_staff)
