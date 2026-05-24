from django.contrib.auth.views import redirect_to_login
from django.shortcuts import redirect
from django.urls import reverse

from appeals.permissions import (
    ADD_APPEAL_PERMISSION,
    START_APPEAL_PROCESSING_PERMISSION,
    VIEW_APPEAL_PERMISSION,
)


def post_login_redirect(request):
    """Направляет пользователя после входа в наиболее подходящий раздел.

    Раздел определяется по правам: сотрудники с доступом в админку — в панель
    администратора, оператор и ответственный сотрудник — в кабинет обращений.
    Остальные возвращаются на публичную главную страницу.
    """
    user = request.user
    if not user.is_authenticated:
        return redirect_to_login(reverse("post_login"))

    if user.is_staff:
        return redirect("admin:index")
    if user.has_perm(VIEW_APPEAL_PERMISSION) and (
        user.has_perm(ADD_APPEAL_PERMISSION) or user.has_perm(START_APPEAL_PROCESSING_PERMISSION)
    ):
        return redirect("appeals:appeal_list")
    return redirect("public:home")
