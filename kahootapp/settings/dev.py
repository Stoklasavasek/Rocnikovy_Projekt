"""
Vývojové nastavení pro Django aplikaci.

Toto nastavení se používá při vývoji aplikace na lokálním počítači.
Obsahuje méně přísné bezpečnostní nastavení pro snadnější vývoj.
"""
from .base import *

# SECURITY WARNING: don't run with debug turned on in production!
# V DEBUG režimu se zobrazují detailní chybové stránky
DEBUG = True

# SECURITY WARNING: keep the secret key used in production secret!
# Tento klíč je pouze pro vývoj - v produkci musí být jiný!
SECRET_KEY = "django-insecure-#%l)f@pcafu_ut3)w94c3a^w9yz#2e5zts4e-&(&*$-3as9y69"

# SECURITY WARNING: define the correct hosts in production!
# V produkci musí být seznam konkrétních domén, ne "*"
ALLOWED_HOSTS = ["*"]

# E-maily se v DEBUG režimu pouze vypisují do konzole (neodesílají se)
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

# Načtení lokálních nastavení (pokud existují)
# Umožňuje přepsat nastavení pro konkrétní vývojové prostředí
try:
    from .local import *
except ImportError:
    pass
