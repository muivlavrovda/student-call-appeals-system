from django.contrib import admin
from django.utils.translation import gettext_lazy as _

from appeals.access import can_view_appeal, visible_appeals_for
from appeals.models import (
    Appeal,
    AppealCategory,
    AppealComment,
    AppealHistoryEvent,
    Department,
)


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "is_active",
        "created_at",
        "updated_at",
    )
    list_filter = ("is_active",)
    search_fields = (
        "name",
        "description",
        "members__email",
        "members__first_name",
        "members__last_name",
    )
    filter_horizontal = ("members",)
    readonly_fields = (
        "name_key",
        "created_at",
        "updated_at",
    )
    fieldsets = (
        (
            None,
            {
                "fields": (
                    "name",
                    "name_key",
                    "description",
                    "members",
                    "is_active",
                )
            },
        ),
        (
            _("Dates"),
            {
                "fields": (
                    "created_at",
                    "updated_at",
                )
            },
        ),
    )


@admin.register(AppealCategory)
class AppealCategoryAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "department",
        "default_processing_days",
        "is_active",
        "created_at",
        "updated_at",
    )
    list_filter = (
        "department",
        "is_active",
    )
    search_fields = (
        "name",
        "description",
        "department__name",
    )
    readonly_fields = (
        "name_key",
        "created_at",
        "updated_at",
    )
    autocomplete_fields = ("department",)
    fieldsets = (
        (
            None,
            {
                "fields": (
                    "name",
                    "name_key",
                    "department",
                    "default_processing_days",
                    "description",
                    "is_active",
                )
            },
        ),
        (
            _("Dates"),
            {
                "fields": (
                    "created_at",
                    "updated_at",
                )
            },
        ),
    )


class AppealCommentInline(admin.TabularInline):
    model = AppealComment
    extra = 0
    can_delete = False
    fields = (
        "author",
        "text",
        "created_at",
    )
    readonly_fields = fields
    ordering = ("created_at", "-pk")

    def has_add_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_view_permission(self, request, obj=None):
        return obj is not None and can_view_appeal(request.user, obj)


class AppealHistoryEventInline(admin.TabularInline):
    model = AppealHistoryEvent
    extra = 0
    can_delete = False
    fields = (
        "actor",
        "event_type",
        "message",
        "created_at",
    )
    readonly_fields = fields
    ordering = ("created_at", "-pk")

    def has_add_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_view_permission(self, request, obj=None):
        return obj is not None and can_view_appeal(request.user, obj)


@admin.register(Appeal)
class AppealAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "summary",
        "student_full_name",
        "student_phone",
        "category",
        "department",
        "status",
        "is_overdue",
        "due_at",
        "created_by",
        "accepted_by",
        "created_at",
    )
    list_filter = (
        "status",
        "category",
        "department",
        "created_at",
        "due_at",
        "closed_at",
    )
    search_fields = (
        "summary",
        "description",
        "student_full_name",
        "student_phone",
        "result",
        "created_by__email",
        "accepted_by__email",
    )
    autocomplete_fields = (
        "category",
        "department",
    )
    readonly_fields = (
        "status",
        "created_by",
        "accepted_by",
        "accepted_at",
        "closed_at",
        "created_at",
        "updated_at",
    )
    inlines = (
        AppealCommentInline,
        AppealHistoryEventInline,
    )
    fieldsets = (
        (
            _("Student"),
            {
                "fields": (
                    "student_full_name",
                    "student_phone",
                )
            },
        ),
        (
            _("Appeal"),
            {
                "fields": (
                    "summary",
                    "description",
                    "category",
                    "department",
                    "status",
                    "due_at",
                    "result",
                )
            },
        ),
        (
            _("Workflow"),
            {
                "fields": (
                    "created_by",
                    "accepted_by",
                    "accepted_at",
                    "closed_at",
                )
            },
        ),
        (
            _("Dates"),
            {
                "fields": (
                    "created_at",
                    "updated_at",
                )
            },
        ),
    )

    def get_queryset(self, request):
        return (
            visible_appeals_for(request.user)
            .select_related(
                "category",
                "department",
                "created_by",
                "accepted_by",
            )
            .order_by("-created_at", "-pk")
        )

    def has_view_permission(self, request, obj=None):
        if obj is None:
            return request.user.has_perm("appeals.view_appeal")
        return can_view_appeal(request.user, obj)

    def has_change_permission(self, request, obj=None):
        if obj is None:
            return request.user.has_perm("appeals.change_appeal")
        return request.user.has_perm("appeals.change_appeal") and can_view_appeal(
            request.user,
            obj,
        )

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    @admin.display(
        boolean=True,
        description=_("Overdue"),
    )
    def is_overdue(self, obj):
        return obj.is_overdue


@admin.register(AppealComment)
class AppealCommentAdmin(admin.ModelAdmin):
    list_display = (
        "appeal",
        "author",
        "created_at",
    )
    list_filter = ("created_at",)
    search_fields = (
        "text",
        "appeal__summary",
        "author__email",
    )
    readonly_fields = (
        "appeal",
        "author",
        "text",
        "created_at",
    )
    fields = readonly_fields

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(AppealHistoryEvent)
class AppealHistoryEventAdmin(admin.ModelAdmin):
    list_display = (
        "appeal",
        "event_type",
        "actor",
        "created_at",
    )
    list_filter = (
        "event_type",
        "created_at",
    )
    search_fields = (
        "message",
        "appeal__summary",
        "actor__email",
    )
    readonly_fields = (
        "appeal",
        "actor",
        "event_type",
        "message",
        "created_at",
    )
    fields = readonly_fields

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
