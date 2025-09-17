from wagtail.models import Page
from wagtail.fields import StreamField
from wagtail.admin.panels import FieldPanel
from wagtail import blocks

class QuizPage(Page):
    body = StreamField([
        ('question', blocks.StructBlock([
            ('text', blocks.TextBlock()),
            ('answer_a', blocks.TextBlock()),
            ('answer_b', blocks.TextBlock()),
            ('answer_c', blocks.TextBlock()),
            ('answer_d', blocks.TextBlock()),
        ]))
    ], blank=True)

    content_panels = Page.content_panels + [
        FieldPanel('body')
    ]
