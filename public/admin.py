from django.contrib import admin
from django.utils.translation import gettext_lazy as _

from public.models import Feedback


@admin.register(Feedback)
class FeedbackAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "email",
        "is_processed",
        "created_at",
    )
    list_filter = (
        "is_processed",
        "created_at",
    )
    search_fields = (
        "name",
        "email",
        "message",
    )
    readonly_fields = (
        "name",
        "email",
        "message",
        "created_at",
    )
    fieldsets = (
        (
            None,
            {
                "fields": (
                    "name",
                    "email",
                    "message",
                )
            },
        ),
        (
            _("Processing"),
            {
                "fields": (
                    "is_processed",
                    "created_at",
                )
            },
        ),
    )

    def has_add_permission(self, request):
        return False
