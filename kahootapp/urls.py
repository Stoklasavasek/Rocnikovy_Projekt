from django.conf import settings
from django.urls import include, path
from django.contrib import admin


from wagtail.admin import urls as wagtailadmin_urls
from wagtail.documents import urls as wagtaildocs_urls
from wagtail import urls as wagtail_urls

from quiz import views as quiz_views

urlpatterns = [
    path("", quiz_views.landing, name="landing"),
    path("django-admin/", admin.site.urls),
    path("admin/", include(wagtailadmin_urls)),
    path("documents/", include(wagtaildocs_urls)),
    path("accounts/", include("allauth.urls")),
    path("quiz/", quiz_views.quiz_list, name="quiz_list"),
    path("quiz/<int:quiz_id>/start/", quiz_views.quiz_start, name="quiz_start"),
    path("quiz/join/", quiz_views.join_quiz_by_code, name="quiz_join"),
    path("quiz/create/", quiz_views.quiz_create, name="quiz_create"),
    path("quiz/<int:quiz_id>/edit/", quiz_views.quiz_update, name="quiz_update"),
    path("quiz/<int:quiz_id>/delete/", quiz_views.quiz_delete, name="quiz_delete"),
    path("quiz/<int:quiz_id>/session/create/", quiz_views.session_create, name="session_create"),
    path("session/<str:hash>/", quiz_views.session_lobby, name="session_lobby"),
    path("session/<str:hash>/q/<int:order>/start/", quiz_views.session_start_question, name="session_start_question"),
    path("session/<str:hash>/current/", quiz_views.session_current_question, name="session_current_question"),
    path("session/<str:hash>/status/", quiz_views.session_status, name="session_status"),
    path("session/<str:hash>/q/<int:order>/", quiz_views.session_question_view, name="session_question_view"),
    path("session/<str:hash>/q/<int:order>/submit/", quiz_views.session_submit_answer, name="session_submit_answer"),
    path("session/<str:hash>/q/<int:order>/joker/", quiz_views.session_use_joker, name="session_use_joker"),
    path("session/<str:hash>/finish/", quiz_views.session_finish, name="session_finish"),
    path("session/<str:hash>/results/", quiz_views.session_results, name="session_results"),
    path("session/<str:hash>/results.csv", quiz_views.session_results_csv, name="session_results_csv"),
]

if settings.DEBUG:
    from django.conf.urls.static import static
    from django.contrib.staticfiles.urls import staticfiles_urlpatterns

    urlpatterns += staticfiles_urlpatterns()
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

urlpatterns += [
    path("", include(wagtail_urls)),
]
