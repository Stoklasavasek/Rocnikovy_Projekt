"""Role a oprávnění pro kvízy."""

TEACHER_GROUP = "Teacher"


def user_is_teacher(user) -> bool:
    """Zkontroluje, zda je uživatel učitel."""
    return user.is_authenticated and (user.groups.filter(name=TEACHER_GROUP).exists() or user.is_staff)
