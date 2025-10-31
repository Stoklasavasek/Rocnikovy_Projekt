from functools import wraps
from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponseForbidden


TEACHER_GROUP = "Teacher"


def user_is_teacher(user) -> bool:
    if not user.is_authenticated:
        return False
    return user.groups.filter(name=TEACHER_GROUP).exists() or user.is_staff


def teacher_required(view_func):
    @login_required
    @wraps(view_func)
    def _wrapped(request: HttpRequest, *args, **kwargs):
        if not user_is_teacher(request.user):
            return HttpResponseForbidden("Pouze pro učitele.")
        return view_func(request, *args, **kwargs)

    return _wrapped


