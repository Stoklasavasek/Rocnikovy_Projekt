from django.db import models
from django.core.exceptions import ValidationError
from django.apps import apps

from wagtail.models import Page
from wagtail.fields import RichTextField
from wagtail.admin.panels import FieldPanel, MultiFieldPanel
from wagtail.documents.models import Document


class HomePage(Page):
    """
    Jednoduchá Wagtail stránka pro úvod / welcome screen.

    Šablona se bere z `home/templates/home/home_page.html`, obsah se zatím
    neřeší přes další Wagtail panely (jde hlavně o routování na landing).
    """

    pass


class EducationalMaterial(Page):
    """
    Vzdělávací materiály propojené s kvízy.
    
    Učitelé mohou vytvářet vzdělávací materiály (texty, obrázky, odkazy),
    které jsou propojené s konkrétními kvízy. Studenti je mohou zobrazit
    před nebo po kvízu pro lepší pochopení látky.
    
    Materiály se spravují přes Wagtail admin rozhraní.
    """
    related_quiz = models.ForeignKey(
        'quiz.Quiz',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        help_text="Kvíz, ke kterému se materiál vztahuje (volitelné)",
        verbose_name="Související kvíz",
        related_name='educational_materials'
    )
    material_type = models.CharField(
        max_length=50,
        choices=[
            ('text', 'Textový materiál'),
            ('video', 'Video'),
            ('link', 'Externí odkaz'),
            ('document', 'Dokument'),
        ],
        default='text',
        verbose_name="Typ materiálu"
    )
    content = RichTextField(blank=True, verbose_name="Obsah materiálu")
    external_url = models.URLField(
        blank=True,
        help_text="URL pro externí materiál (video, dokument, atd.)",
        verbose_name="Externí URL"
    )
    video_file = models.ForeignKey(
        Document,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='educational_materials_video',
        help_text="Nahrané video (pouze pro typ 'Video')",
        verbose_name="Video soubor"
    )
    document_file = models.ForeignKey(
        Document,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='educational_materials_document',
        help_text="Nahraný dokument (pouze pro typ 'Dokument')",
        verbose_name="Dokument soubor"
    )
    show_before_quiz = models.BooleanField(
        default=True,
        help_text="Zobrazit materiál před kvízem",
        verbose_name="Zobrazit před kvízem"
    )
    show_after_quiz = models.BooleanField(
        default=False,
        help_text="Zobrazit materiál po kvízu",
        verbose_name="Zobrazit po kvízu"
    )
    
    content_panels = Page.content_panels + [
        FieldPanel('related_quiz'),
        FieldPanel('material_type'),
        FieldPanel('content'),
        FieldPanel('external_url'),
        FieldPanel('video_file'),
        FieldPanel('document_file'),
        MultiFieldPanel([
            FieldPanel('show_before_quiz'),
            FieldPanel('show_after_quiz'),
        ], heading="Zobrazení"),
    ]
    
    def clean(self):
        """
        Validace materiálu.
        
        Note:
            Validace není potřeba, ForeignKey to řeší automaticky.
            Tato metoda je zde pro případné budoucí rozšíření validace.
        """
        pass
    
    def get_related_quiz(self):
        """
        Vrátí související kvíz, pokud existuje.
        
        Returns:
            Quiz objekt nebo None
        """
        return self.related_quiz
    
    # Nastavení, pod jakými stránkami může být EducationalMaterial vytvořen
    parent_page_types = ['home.HomePage']  # Může být vytvořen pod HomePage
    
    # Nastavení, jaké typy stránek mohou být vytvořeny pod EducationalMaterial
    subpage_types = []  # EducationalMaterial nemůže mít podstránky
    
    class Meta:
        verbose_name = "Vzdělávací materiál"
        verbose_name_plural = "Vzdělávací materiály"
