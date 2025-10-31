from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from django.db.models.signals import post_migrate
from django.dispatch import receiver

from allauth.account.signals import user_signed_up


TEACHER_GROUP = "Teacher"
STUDENT_GROUP = "Student"


def ensure_role_groups_exist() -> None:
    Group.objects.get_or_create(name=TEACHER_GROUP)
    Group.objects.get_or_create(name=STUDENT_GROUP)


@receiver(post_migrate)
def create_default_groups(sender, **kwargs):
    ensure_role_groups_exist()
    # Po migraci také přiřadíme učitelům oprávnění k modelům z app 'quiz'
    try:
        teacher_group = Group.objects.get(name=TEACHER_GROUP)

        # Najdi content types pro app 'quiz'
        quiz_cts = ContentType.objects.filter(app_label="quiz", model__in=[
            "quiz", "question", "answer", "studentanswer",
        ])

        # Mapování model -> sady kódů oprávnění
        per_model_perms = {
            "quiz": {"add_quiz", "change_quiz", "delete_quiz", "view_quiz"},
            "question": {"add_question", "change_question", "delete_question", "view_question"},
            "answer": {"add_answer", "change_answer", "delete_answer", "view_answer"},
            # U StudentAnswer typicky jen view
            "studentanswer": {"view_studentanswer"},
        }

        # Pro každý content type najdi požadovaná Permission a přidej je do skupiny Teacher
        for ct in quiz_cts:
            wanted_codenames = per_model_perms.get(ct.model, set())
            if not wanted_codenames:
                continue
            perms = Permission.objects.filter(content_type=ct, codename__in=wanted_codenames)
            teacher_group.permissions.add(*perms)
    except Exception:
        # Při prvních migracích nemusí být permissions ještě dostupné; bezpečně ignoruj
        pass


@receiver(user_signed_up)
def assign_student_group_on_signup(request, user, **kwargs):
    ensure_role_groups_exist()
    student_group = Group.objects.get(name=STUDENT_GROUP)
    user.groups.add(student_group)
    user.save(update_fields=["last_login"])  # touch user to trigger signals minimally


