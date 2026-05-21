from django.contrib import admin
from django.urls import include, path
from django.utils.translation import gettext_lazy as _

admin.site.site_header = _("Appeals administration")
admin.site.site_title = _("Appeals admin")
admin.site.index_title = _("Appeals administration")

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("public.urls")),
]
