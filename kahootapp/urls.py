from django.conf import settings
from django.urls import include, path
from django.contrib import admin


from wagtail.admin import urls as wagtailadmin_urls
from wagtail.documents import urls as wagtaildocs_urls
from wagtail import urls as wagtail_urls

from search import views as search_views
from quiz import views as quiz_views

urlpatterns = [
    # Custom landing page (overrides Wagtail root)
    path("", quiz_views.landing, name="landing"),
    # Django admin
    path("django-admin/", admin.site.urls),

    # Wagtail admin
    path("admin/", include(wagtailadmin_urls)),

    # Dokumenty Wagtail
    path("documents/", include(wagtaildocs_urls)),

    # Allauth login / logout / signup
    path("accounts/", include("allauth.urls")),  # ← musí být **před wagtail_urls**

    # Hledání
    path("search/", search_views.search, name="search"),

    # Kvízy
    path("quiz/", quiz_views.quiz_list, name="quiz_list"),
    path("quiz/<int:quiz_id>/start/", quiz_views.quiz_start, name="quiz_start"),
    path("quiz/join/", quiz_views.join_quiz_by_code, name="quiz_join"),
    path("quiz/create/", quiz_views.quiz_create, name="quiz_create"),
    path("quiz/<int:quiz_id>/edit/", quiz_views.quiz_update, name="quiz_update"),
    path("quiz/<int:quiz_id>/questions/", quiz_views.quiz_questions, name="quiz_questions"),
    path("quiz/question/<int:question_id>/answers/", quiz_views.question_answers, name="question_answers"),
    path("quiz/<int:quiz_id>/delete/", quiz_views.quiz_delete, name="quiz_delete"),
    # Live session routes
    path("quiz/<int:quiz_id>/session/create/", quiz_views.session_create, name="session_create"),
    path("session/<str:code>/", quiz_views.session_lobby, name="session_lobby"),
    path("session/<str:code>/q/<int:order>/start/", quiz_views.session_start_question, name="session_start_question"),
    path("session/<str:code>/current/", quiz_views.session_current_question, name="session_current_question"),
    path("session/<str:code>/status/", quiz_views.session_status, name="session_status"),
    path("session/<str:code>/q/<int:order>/", quiz_views.session_question_view, name="session_question_view"),
    path("session/<str:code>/q/<int:order>/submit/", quiz_views.session_submit_answer, name="session_submit_answer"),
    path("session/<str:code>/finish/", quiz_views.session_finish, name="session_finish"),
    path("session/<str:code>/results/", quiz_views.session_results, name="session_results"),
    path("session/<str:code>/results.csv", quiz_views.session_results_csv, name="session_results_csv"),
]

if settings.DEBUG:
    from django.conf.urls.static import static
    from django.contrib.staticfiles.urls import staticfiles_urlpatterns

    urlpatterns += staticfiles_urlpatterns()
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

# Nakonec Wagtail pages
urlpatterns += [
    path("", include(wagtail_urls)),  # musí být **na konci**
]
