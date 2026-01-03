"""
Management command pro opravu Wagtail oprávnění u učitelů.

Tento command přiřadí učitelům oprávnění k přístupu do Wagtail adminu
a k editaci stránek.
"""
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User, Group as DjangoGroup, Permission
from django.contrib.contenttypes.models import ContentType

TEACHER_GROUP = "Teacher"

# Wagtail importy
try:
    from wagtail.models import Page, GroupPagePermission
    WAGTAIL_AVAILABLE = True
except ImportError as e:
    WAGTAIL_AVAILABLE = False
    WAGTAIL_ERROR = str(e)


class Command(BaseCommand):
    help = 'Přiřadí Wagtail oprávnění všem učitelům'

    def handle(self, *args, **options):
        if not WAGTAIL_AVAILABLE:
            error_msg = globals().get('WAGTAIL_ERROR', 'Unknown error')
            self.stdout.write(
                self.style.ERROR(f'Wagtail není nainstalován: {error_msg}')
            )
            return
        
        try:
            teacher_group = DjangoGroup.objects.get(name=TEACHER_GROUP)
            teachers = User.objects.filter(groups=teacher_group)
            
            # Oprávnění k přístupu do Wagtail adminu
            access_admin_perm = Permission.objects.filter(
                codename='access_admin',
                content_type__app_label='wagtailadmin'
            ).first()
            
            if not access_admin_perm:
                self.stdout.write(
                    self.style.ERROR('Oprávnění access_admin nebylo nalezeno.')
                )
                return
            
            # Získání root stránky
            root_page = Page.objects.filter(depth=1).first()
            if not root_page:
                self.stdout.write(
                    self.style.ERROR('Root stránka neexistuje. Spusťte nejprve migrace.')
                )
                return
            
            # Získání oprávnění k editaci stránek
            page_content_type = ContentType.objects.filter(
                app_label='wagtailcore',
                model='page'
            ).first()
            
            if page_content_type:
                add_perm = Permission.objects.filter(
                    content_type=page_content_type,
                    codename='add_page'
                ).first()
                change_perm = Permission.objects.filter(
                    content_type=page_content_type,
                    codename='change_page'
                ).first()
                publish_perm = Permission.objects.filter(
                    content_type=page_content_type,
                    codename='publish_page'
                ).first()
                
                # Přiřazení oprávnění k root stránce pro Django skupinu Teacher
                if add_perm:
                    GroupPagePermission.objects.get_or_create(
                        page=root_page,
                        group=teacher_group,
                        permission=add_perm
                    )
                if change_perm:
                    GroupPagePermission.objects.get_or_create(
                        page=root_page,
                        group=teacher_group,
                        permission=change_perm
                    )
                if publish_perm:
                    GroupPagePermission.objects.get_or_create(
                        page=root_page,
                        group=teacher_group,
                        permission=publish_perm
                    )
            
            # Přiřazení oprávnění k přístupu do adminu skupině
            teacher_group.permissions.add(access_admin_perm)
            
            # Zajištění, že všichni učitelé mají is_staff=True
            teachers.filter(is_staff=False).update(is_staff=True)
            
            # Přiřazení oprávnění přímo všem učitelům
            for teacher in teachers:
                teacher.user_permissions.add(access_admin_perm)
            
            count = teachers.count()
            
            self.stdout.write(
                self.style.SUCCESS(
                    f'Úspěšně přiřazena Wagtail oprávnění pro {count} učitelů. '
                    f'Skupina "{TEACHER_GROUP}" má nyní přístup do Wagtail adminu.'
                )
            )
        except DjangoGroup.DoesNotExist:
            self.stdout.write(
                self.style.ERROR(
                    f'Django skupina "{TEACHER_GROUP}" neexistuje. Spusťte nejprve migrace.'
                )
            )