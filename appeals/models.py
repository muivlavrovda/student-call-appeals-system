import re
from collections.abc import Callable, Mapping
from typing import Any, ClassVar

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from appeals.permissions import (
    CLOSE_APPEAL_CODENAME,
    COMMENT_APPEAL_CODENAME,
    START_APPEAL_PROCESSING_CODENAME,
    TRANSFER_APPEAL_CODENAME,
)

PHONE_RE = re.compile(r"^7\d{10}$")
NormalizedFields = Mapping[str, Callable[[str], str]]


def normalize_model_fields(
    instance: models.Model,
    fields: NormalizedFields,
) -> None:
    for field_name, normalizer in fields.items():
        value = getattr(instance, field_name)
        if isinstance(value, str):
            setattr(instance, field_name, normalizer(value))


def normalize_spaces(value: str) -> str:
    return " ".join(value.split())


def normalize_name_key(value: str) -> str:
    return normalize_spaces(value).casefold()


def validate_phone(value: str) -> None:
    if value and not PHONE_RE.fullmatch(normalize_phone(value)):
        raise ValidationError(_("Enter a valid Russian phone number."))


def normalize_phone(value: str) -> str:
    digits = "".join(char for char in value if char.isdigit())
    if len(digits) == 10:
        return f"7{digits}"
    if len(digits) == 11 and digits.startswith("8"):
        return f"7{digits[1:]}"
    return digits


def normalize_named_instance(instance: models.Model) -> None:
    normalize_model_fields(instance, instance.NORMALIZED_FIELDS)
    instance.name_key = normalize_name_key(instance.name)


class Department(models.Model):
    NORMALIZED_FIELDS: ClassVar[NormalizedFields] = {
        "name": normalize_spaces,
    }

    name = models.CharField(
        _("Name"),
        max_length=150,
    )

    name_key = models.CharField(
        _("Name key"),
        max_length=255,
        blank=True,
        editable=False,
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
        ordering = ["name", "-pk"]
        constraints = [
            models.UniqueConstraint(
                fields=["name_key"],
                name="unique_department_name_key",
                violation_error_message=_("Department with this name already exists."),
            ),
        ]

    def __str__(self) -> str:
        return self.name

    def save(self, *args: Any, **kwargs: Any) -> None:
        normalize_named_instance(self)
        super().save(*args, **kwargs)

    def clean(self) -> None:
        normalize_named_instance(self)


class AppealCategory(models.Model):
    NORMALIZED_FIELDS: ClassVar[NormalizedFields] = {
        "name": normalize_spaces,
    }

    name = models.CharField(
        _("Name"),
        max_length=150,
    )

    name_key = models.CharField(
        _("Name key"),
        max_length=255,
        blank=True,
        editable=False,
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
        validators=[
            MinValueValidator(1),
        ],
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
        ordering = ["name", "-pk"]
        constraints = [
            models.UniqueConstraint(
                fields=["name_key"],
                name="unique_appeal_category_name_key",
                violation_error_message=_("Appeal category with this name already exists."),
            ),
        ]

    def __str__(self) -> str:
        return self.name

    def save(self, *args: Any, **kwargs: Any) -> None:
        normalize_named_instance(self)
        super().save(*args, **kwargs)

    def clean(self) -> None:
        normalize_named_instance(self)


class Appeal(models.Model):
    NORMALIZED_FIELDS: ClassVar[NormalizedFields] = {
        "student_full_name": normalize_spaces,
        "student_phone": normalize_phone,
        "summary": normalize_spaces,
    }

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
        validators=[
            validate_phone,
        ],
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
        ordering = ["-created_at", "-pk"]
        permissions = [
            (START_APPEAL_PROCESSING_CODENAME, _("Can start appeal processing")),
            (COMMENT_APPEAL_CODENAME, _("Can comment appeal")),
            (CLOSE_APPEAL_CODENAME, _("Can close appeal")),
            (TRANSFER_APPEAL_CODENAME, _("Can transfer appeal")),
        ]

    def __str__(self) -> str:
        return f"#{self.pk} {self.summary}" if self.pk else self.summary

    def save(self, *args: Any, **kwargs: Any) -> None:
        normalize_model_fields(self, self.NORMALIZED_FIELDS)
        super().save(*args, **kwargs)


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
        ordering = ["created_at", "-pk"]

    def __str__(self) -> str:
        return _("Comment for appeal #{id}").format(id=self.appeal_id)


class AppealHistoryEvent(models.Model):
    class EventType(models.TextChoices):
        CREATED = "created", _("Created")
        CATEGORY_CHANGED = "category_changed", _("Category changed")
        DEPARTMENT_CHANGED = "department_changed", _("Department changed")
        DUE_AT_CHANGED = "due_at_changed", _("Due date changed")
        ACCEPTED = "accepted", _("Accepted")
        STATUS_CHANGED = "status_changed", _("Status changed")
        COMMENT_ADDED = "comment_added", _("Comment added")
        RESULT_UPDATED = "result_updated", _("Result updated")
        CLOSED = "closed", _("Closed")

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
        max_length=50,
        choices=EventType.choices,
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
        ordering = ["created_at", "-pk"]

    def __str__(self) -> str:
        return _("History event for appeal #{id}").format(id=self.appeal_id)
