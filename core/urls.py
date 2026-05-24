from django.contrib import admin
from django.contrib.auth.views import LoginView
from django.urls import include, path
from django.utils.translation import gettext_lazy as _

from core.views import post_login_redirect
from users.forms import LoginForm

admin.site.site_header = _("Appeals administration")
admin.site.site_title = _("Appeals admin")
admin.site.index_title = _("Appeals administration")

urlpatterns = [
    path("admin/", admin.site.urls),
    path(
        "accounts/login/",
        LoginView.as_view(
            authentication_form=LoginForm,
            extra_context={"breadcrumbs": [{"label": "Вход"}]},
        ),
        name="login",
    ),
    path("accounts/", include("django.contrib.auth.urls")),
    path("accounts/post-login/", post_login_redirect, name="post_login"),
    path("cabinet/", include("appeals.urls")),
    path("", include("public.urls")),
]
