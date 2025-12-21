from django.db import models

from wagtail.models import Page


class HomePage(Page):
    """
    Jednoduchá Wagtail stránka pro úvod / welcome screen.

    Šablona se bere z `home/templates/home/home_page.html`, obsah se zatím
    neřeší přes další Wagtail panely (jde hlavně o routování na landing).
    """

    pass
