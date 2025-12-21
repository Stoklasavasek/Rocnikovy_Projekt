"""Signály pro správu uživatelských rolí a oprávnění."""
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from django.db.models.signals import post_migrate
from django.dispatch import receiver

from allauth.account.signals import user_signed_up

TEACHER_GROUP = "Teacher"
STUDENT_GROUP = "Student"

QUIZ_PERMISSIONS = {
    "quiz": {"add_quiz", "change_quiz", "delete_quiz", "view_quiz"},
    "question": {"add_question", "change_question", "delete_question", "view_question"},
    "answer": {"add_answer", "change_answer", "delete_answer", "view_answer"},
    "studentanswer": {"view_studentanswer"},
}


def ensure_role_groups_exist():
    """Vytvoří skupiny Teacher a Student, pokud neexistují."""
    Group.objects.get_or_create(name=TEACHER_GROUP)
    Group.objects.get_or_create(name=STUDENT_GROUP)


def assign_quiz_permissions():
    """Přiřadí oprávnění k quiz modelům pro obě skupiny."""
    try:
        teacher_group = Group.objects.get(name=TEACHER_GROUP)
        student_group = Group.objects.get(name=STUDENT_GROUP)
        for ct in ContentType.objects.filter(app_label="quiz", model__in=QUIZ_PERMISSIONS.keys()):
            wanted_codenames = QUIZ_PERMISSIONS.get(ct.model, set())
            if wanted_codenames:
                perms = Permission.objects.filter(content_type=ct, codename__in=wanted_codenames)
                teacher_group.permissions.add(*perms)
                student_group.permissions.add(*perms)
    except Exception:
        pass


@receiver(post_migrate)
def create_default_groups(sender, **kwargs):
    """Vytvoří výchozí skupiny a přiřadí oprávnění po migraci."""
    ensure_role_groups_exist()
    assign_quiz_permissions()


@receiver(user_signed_up)
def assign_student_group_on_signup(request, user, **kwargs):
    """Přiřadí novému uživateli skupinu Student při registraci."""
    ensure_role_groups_exist()
    user.groups.add(Group.objects.get(name=STUDENT_GROUP))
    user.save(update_fields=["last_login"])
