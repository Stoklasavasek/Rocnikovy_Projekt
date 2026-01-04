"""
Signály pro správu uživatelských rolí a oprávnění.

CO TO DĚLÁ:
Automaticky vytváří skupiny "Teacher" a "Student" a přiřazuje oprávnění.
Když se uživatel zaregistruje, automaticky se přidá do skupiny "Student".
Když se uživatel přidá do skupiny "Teacher", automaticky dostane:
- is_staff=True (přístup do Django/Wagtail adminu)
- Oprávnění k vytváření a správě kvízů
- Oprávnění k nahrávání dokumentů (videa, PDF) v Wagtail adminu

PROČ TO POTŘEBUJEME:
Aby učitelé mohli vytvářet kvízy, spouštět živá sezení a nahrávat vzdělávací materiály
bez nutnosti ručního nastavování oprávnění v Django adminu.
"""
from django.contrib.auth.models import Group, Permission, User
from django.contrib.contenttypes.models import ContentType
from django.db.models.signals import post_migrate, m2m_changed
from django.dispatch import receiver

from allauth.account.signals import user_signed_up

# Wagtail importy pro správu oprávnění
try:
    from wagtail.models import Page
    WAGTAIL_AVAILABLE = True
except ImportError:
    WAGTAIL_AVAILABLE = False

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


def assign_wagtail_document_permissions():
    """
    Přiřadí učitelům oprávnění pro správu dokumentů (videa, PDF, atd.).
    
    Učitelé potřebují oprávnění k dokumentům, aby mohli:
    - Nahrávat videa a dokumenty do Wagtail adminu
    - Propojovat je s EducationalMaterial stránkami
    - Zobrazit menu "Dokumenty" v Wagtail adminu (vyžaduje view_document)
    
    Note:
        Tato oprávnění se přiřazují automaticky při migraci přes post_migrate signal.
    """
    try:
        teacher_group = Group.objects.get(name=TEACHER_GROUP)
        document_content_type = ContentType.objects.filter(
            app_label='wagtaildocs',
            model='document'
        ).first()
        
        if document_content_type:
            # Přidáme také view_document, aby se zobrazilo menu "Dokumenty"
            document_perms = Permission.objects.filter(
                content_type=document_content_type,
                codename__in=['add_document', 'change_document', 'delete_document', 'view_document']
            )
            teacher_group.permissions.add(*document_perms)
    except Exception:
        pass


def ensure_teachers_have_staff_access():
    """Zajistí, že všichni učitelé mají is_staff=True pro přístup do Wagtail adminu."""
    try:
        teacher_group = Group.objects.get(name=TEACHER_GROUP)
        teachers = User.objects.filter(groups=teacher_group, is_staff=False)
        if teachers.exists():
            teachers.update(is_staff=True)
    except Group.DoesNotExist:
        pass


@receiver(post_migrate)
def create_default_groups(sender, **kwargs):
    """Vytvoří výchozí skupiny a přiřadí oprávnění po migraci."""
    ensure_role_groups_exist()
    assign_quiz_permissions()
    assign_wagtail_document_permissions()
    ensure_teachers_have_staff_access()


@receiver(user_signed_up)
def assign_student_group_on_signup(request, user, **kwargs):
    """Přiřadí novému uživateli skupinu Student při registraci."""
    ensure_role_groups_exist()
    user.groups.add(Group.objects.get(name=STUDENT_GROUP))
    user.save(update_fields=["last_login"])


def assign_wagtail_permissions_to_teacher(user):
    """
    Přiřadí učiteli oprávnění k přístupu do Wagtail adminu a správu dokumentů.
    
    Oprávnění k editaci stránek se přiřazují přes skupinu automaticky.
    Tato funkce se volá automaticky při přidání uživatele do skupiny Teacher
    (přes m2m_changed signal).
    
    Args:
        user: Django User objekt učitele
    
    Note:
        - access_admin: Povolí přístup do Wagtail adminu
        - Dokumenty: Umožní nahrávat a spravovat dokumenty (videa, PDF, atd.)
    """
    if not WAGTAIL_AVAILABLE:
        return
    
    try:
        # Oprávnění k přístupu do Wagtail adminu
        access_admin_perm = Permission.objects.filter(
            codename='access_admin',
            content_type__app_label='wagtailadmin'
        ).first()
        
        if access_admin_perm:
            user.user_permissions.add(access_admin_perm)
        
        # Oprávnění pro správu dokumentů (nahrávání, úprava, mazání)
        document_content_type = ContentType.objects.filter(
            app_label='wagtaildocs',
            model='document'
        ).first()
        
        if document_content_type:
            # Přidáme také view_document, aby se zobrazilo menu
            document_perms = Permission.objects.filter(
                content_type=document_content_type,
                codename__in=['add_document', 'change_document', 'delete_document', 'view_document']
            )
            user.user_permissions.add(*document_perms)
    except Exception:
        pass


@receiver(m2m_changed, sender=User.groups.through)
def update_teacher_staff_status(sender, instance, action, pk_set, **kwargs):
    """
    Automaticky nastaví is_staff=True pro učitele při přidání do skupiny Teacher.
    Tím získají přístup do Wagtail adminu pro správu vzdělávacích materiálů.
    """
    if action == 'post_add':
        teacher_group = Group.objects.filter(name=TEACHER_GROUP).first()
        if teacher_group and teacher_group.pk in pk_set:
            # Uživatel byl přidán do skupiny Teacher - nastavit is_staff
            instance.is_staff = True
            instance.save(update_fields=['is_staff'])
            # Přiřadit Wagtail oprávnění
            assign_wagtail_permissions_to_teacher(instance)
    elif action == 'post_remove':
        teacher_group = Group.objects.filter(name=TEACHER_GROUP).first()
        if teacher_group and teacher_group.pk in pk_set:
            # Uživatel byl odebrán ze skupiny Teacher - zkontrolovat, zda není admin
            # Pokud není superuser, odebrat is_staff
            if not instance.is_superuser:
                instance.is_staff = False
                instance.save(update_fields=['is_staff'])
