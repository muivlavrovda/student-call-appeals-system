from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class AppealsConfig(AppConfig):
    name = "appeals"
    verbose_name = _("Appeals")

    def ready(self) -> None:
        from appeals.roles import register_role_sync

        register_role_sync()
