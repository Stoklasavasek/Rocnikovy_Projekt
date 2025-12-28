"""
Produkční nastavení pro Django aplikaci.

Toto nastavení se používá při nasazení aplikace na produkční server.
Obsahuje optimalizace pro výkon a bezpečnost.
"""
from .base import *

# V produkci musí být DEBUG vypnutý kvůli bezpečnosti
DEBUG = False

# ManifestStaticFilesStorage je doporučený v produkci, aby se zabránilo
# podávání zastaralých JavaScript / CSS souborů z cache
# (např. po upgradu Wagtail).
# Viz: https://docs.djangoproject.com/en/4.2/ref/contrib/staticfiles/#manifeststaticfilesstorage
STORAGES["staticfiles"]["BACKEND"] = "django.contrib.staticfiles.storage.ManifestStaticFilesStorage"

# Načtení lokálních nastavení (pokud existují)
# Umožňuje přepsat nastavení pro konkrétní produkční prostředí
try:
    from .local import *
except ImportError:
    pass
