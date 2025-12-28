"""
Hlavní URL konfigurace pro Django aplikaci.

Definuje všechny URL cesty pro:
- Kvízy (vytváření, úprava, mazání, spuštění)
- Živá sezení (lobby, otázky, odpovědi, výsledky)
- Autentizaci (allauth)
- Admin rozhraní (Django admin a Wagtail)
"""
from django.conf import settings
from django.urls import include, path
from django.contrib import admin


from wagtail.admin import urls as wagtailadmin_urls
from wagtail.documents import urls as wagtaildocs_urls
from wagtail import urls as wagtail_urls

from quiz import views as quiz_views

urlpatterns = [
    # Hlavní stránka
    path("", quiz_views.landing, name="landing"),
    
    # Admin rozhraní
    path("django-admin/", admin.site.urls),  # Django admin
    path("admin/", include(wagtailadmin_urls)),  # Wagtail admin
    path("documents/", include(wagtaildocs_urls)),  # Wagtail dokumenty
    
    # Autentizace (přihlášení, registrace, Microsoft OAuth)
    path("accounts/", include("allauth.urls")),
    
    # Kvízy - základní operace
    path("quiz/", quiz_views.quiz_list, name="quiz_list"),  # Seznam kvízů
    path("quiz/<int:quiz_id>/start/", quiz_views.quiz_start, name="quiz_start"),  # Spuštění jednoduchého kvízu
    path("quiz/join/", quiz_views.join_quiz_by_code, name="quiz_join"),  # Připojení pomocí kódu
    path("quiz/create/", quiz_views.quiz_create, name="quiz_create"),  # Vytvoření kvízu
    path("quiz/<int:quiz_id>/edit/", quiz_views.quiz_update, name="quiz_update"),  # Úprava kvízu
    path("quiz/<int:quiz_id>/delete/", quiz_views.quiz_delete, name="quiz_delete"),  # Smazání kvízu
    
    # Živá sezení
    path("quiz/<int:quiz_id>/session/create/", quiz_views.session_create, name="session_create"),  # Vytvoření sezení
    path("session/<str:hash>/", quiz_views.session_lobby, name="session_lobby"),  # Lobby sezení
    path("session/<str:hash>/q/<int:order>/start/", quiz_views.session_start_question, name="session_start_question"),  # Spuštění otázky
    path("session/<str:hash>/current/", quiz_views.session_current_question, name="session_current_question"),  # Aktuální otázka
    path("session/<str:hash>/status/", quiz_views.session_status, name="session_status"),  # AJAX endpoint pro stav sezení
    path("session/<str:hash>/q/<int:order>/", quiz_views.session_question_view, name="session_question_view"),  # Zobrazení otázky
    path("session/<str:hash>/q/<int:order>/submit/", quiz_views.session_submit_answer, name="session_submit_answer"),  # Odeslání odpovědi
    path("session/<str:hash>/q/<int:order>/joker/", quiz_views.session_use_joker, name="session_use_joker"),  # Použití žolíku
    path("session/<str:hash>/finish/", quiz_views.session_finish, name="session_finish"),  # Ukončení sezení
    path("session/<str:hash>/results/", quiz_views.session_results, name="session_results"),  # Finální výsledky
    path("session/<str:hash>/results.csv", quiz_views.session_results_csv, name="session_results_csv"),  # Export výsledků do CSV
]

# V DEBUG režimu přidáme podporu pro statické soubory a média
if settings.DEBUG:
    from django.conf.urls.static import static
    from django.contrib.staticfiles.urls import staticfiles_urlpatterns

    # Statické soubory (CSS, JS, obrázky)
    urlpatterns += staticfiles_urlpatterns()
    # Média (nahrané soubory uživatelů)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

# Wagtail URL (musí být na konci, aby nezachytávaly ostatní cesty)
urlpatterns += [
    path("", include(wagtail_urls)),
]
