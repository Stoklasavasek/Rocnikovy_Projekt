"""
WSGI konfigurace pro Django aplikaci.

WSGI (Web Server Gateway Interface) je standardní rozhraní mezi
webovým serverem (např. Gunicorn) a Django aplikací.

Tento soubor se používá při nasazení aplikace na produkční server.
"""
import os
from django.core.wsgi import get_wsgi_application

# Nastavení Django settings modulu
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "kahootapp.settings.dev")

# Vytvoření WSGI aplikace
application = get_wsgi_application()
