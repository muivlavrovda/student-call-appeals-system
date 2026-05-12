from django.conf import settings
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _


class Department(models.Model):
    name = models.CharField(
        _("Name"),
        max_length=150,
        unique=True,
    )

    description = models.TextField(
        _("Description"),
        blank=True,
    )

    members = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        verbose_name=_("Members"),
        blank=True,
        related_name="departments",
    )

    is_active = models.BooleanField(
        _("Is active"),
        default=True,
    )

    created_at = models.DateTimeField(
        _("Created at"),
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        _("Updated at"),
        auto_now=True,
    )

    class Meta:
        verbose_name = _("Department")
        verbose_name_plural = _("Departments")
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name


class AppealCategory(models.Model):
    name = models.CharField(
        _("Name"),
        max_length=150,
        unique=True,
    )

    department = models.ForeignKey(
        Department,
        verbose_name=_("Department"),
        on_delete=models.PROTECT,
        related_name="categories",
    )

    default_processing_days = models.PositiveSmallIntegerField(
        _("Default processing days"),
        default=3,
    )

    description = models.TextField(
        _("Description"),
        blank=True,
    )

    is_active = models.BooleanField(
        _("Is active"),
        default=True,
    )

    created_at = models.DateTimeField(
        _("Created at"),
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        _("Updated at"),
        auto_now=True,
    )

    class Meta:
        verbose_name = _("Appeal category")
        verbose_name_plural = _("Appeal categories")
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name


class Appeal(models.Model):
    class Status(models.TextChoices):
        NEW = "new", _("New")
        IN_PROGRESS = "in_progress", _("In progress")
        CLOSED = "closed", _("Closed")

    student_full_name = models.CharField(
        _("Student full name"),
        max_length=255,
    )

    student_phone = models.CharField(
        _("Student phone"),
        max_length=50,
    )

    summary = models.CharField(
        _("Summary"),
        max_length=255,
    )

    description = models.TextField(
        _("Description"),
    )

    category = models.ForeignKey(
        AppealCategory,
        verbose_name=_("Category"),
        on_delete=models.PROTECT,
        related_name="appeals",
    )

    department = models.ForeignKey(
        Department,
        verbose_name=_("Department"),
        on_delete=models.PROTECT,
        related_name="appeals",
    )

    status = models.CharField(
        _("Status"),
        max_length=20,
        choices=Status.choices,
        default=Status.NEW,
    )

    due_at = models.DateTimeField(
        _("Due at"),
    )

    result = models.TextField(
        _("Result"),
        blank=True,
    )

    accepted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name=_("Accepted by"),
        on_delete=models.PROTECT,
        related_name="accepted_appeals",
        blank=True,
        null=True,
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name=_("Created by"),
        on_delete=models.PROTECT,
        related_name="created_appeals",
    )

    created_at = models.DateTimeField(
        _("Created at"),
        default=timezone.now,
    )

    updated_at = models.DateTimeField(
        _("Updated at"),
        auto_now=True,
    )

    accepted_at = models.DateTimeField(
        _("Accepted at"),
        blank=True,
        null=True,
    )

    closed_at = models.DateTimeField(
        _("Closed at"),
        blank=True,
        null=True,
    )

    class Meta:
        verbose_name = _("Appeal")
        verbose_name_plural = _("Appeals")
        ordering = ["-created_at", "-id"]

    def __str__(self) -> str:
        return f"#{self.pk} {self.summary}" if self.pk else self.summary


class AppealComment(models.Model):
    appeal = models.ForeignKey(
        Appeal,
        verbose_name=_("Appeal"),
        on_delete=models.CASCADE,
        related_name="comments",
    )

    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name=_("Author"),
        on_delete=models.PROTECT,
        related_name="appeal_comments",
    )

    text = models.TextField(
        _("Text"),
    )

    created_at = models.DateTimeField(
        _("Created at"),
        default=timezone.now,
    )

    class Meta:
        verbose_name = _("Appeal comment")
        verbose_name_plural = _("Appeal comments")
        ordering = ["created_at", "id"]

    def __str__(self) -> str:
        return _("Comment for appeal #{id}").format(id=self.appeal_id)


class AppealHistoryEvent(models.Model):
    appeal = models.ForeignKey(
        Appeal,
        verbose_name=_("Appeal"),
        on_delete=models.CASCADE,
        related_name="history_events",
    )

    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name=_("Actor"),
        on_delete=models.PROTECT,
        related_name="appeal_history_events",
        blank=True,
        null=True,
    )

    event_type = models.CharField(
        _("Event type"),
        max_length=80,
    )

    message = models.TextField(
        _("Message"),
        blank=True,
    )

    created_at = models.DateTimeField(
        _("Created at"),
        default=timezone.now,
    )

    class Meta:
        verbose_name = _("Appeal history event")
        verbose_name_plural = _("Appeal history events")
        ordering = ["created_at", "id"]

    def __str__(self) -> str:
        return _("History event for appeal #{id}").format(id=self.appeal_id)
