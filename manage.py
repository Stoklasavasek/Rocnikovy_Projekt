#!/usr/bin/env python
"""
Django's command-line utility for administrative tasks.

Použití:
    python manage.py runserver          # Spustí vývojový server
    python manage.py migrate            # Spustí migrace databáze
    python manage.py createsuperuser    # Vytvoří admin uživatele
    python manage.py collectstatic      # Shromáždí statické soubory
"""
import os
import sys


def main():
    """
    Run administrative tasks.
    
    Nastaví Django settings modul a spustí příkaz z příkazové řádky.
    """
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "kahootapp.settings.dev")
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == '__main__':
    main()
