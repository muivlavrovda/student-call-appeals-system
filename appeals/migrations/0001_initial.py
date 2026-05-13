import django.core.validators
import django.db.models.deletion
import django.utils.timezone
from django.conf import settings
from django.db import migrations, models

import appeals.models


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="AppealCategory",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("name", models.CharField(max_length=150, verbose_name="Name")),
                (
                    "name_key",
                    models.CharField(
                        blank=True,
                        editable=False,
                        max_length=255,
                        verbose_name="Name key",
                    ),
                ),
                (
                    "default_processing_days",
                    models.PositiveSmallIntegerField(
                        default=3,
                        validators=[django.core.validators.MinValueValidator(1)],
                        verbose_name="Default processing days",
                    ),
                ),
                (
                    "description",
                    models.TextField(blank=True, verbose_name="Description"),
                ),
                (
                    "is_active",
                    models.BooleanField(default=True, verbose_name="Is active"),
                ),
                (
                    "created_at",
                    models.DateTimeField(auto_now_add=True, verbose_name="Created at"),
                ),
                (
                    "updated_at",
                    models.DateTimeField(auto_now=True, verbose_name="Updated at"),
                ),
            ],
            options={
                "verbose_name": "Appeal category",
                "verbose_name_plural": "Appeal categories",
                "ordering": ["name", "-pk"],
            },
        ),
        migrations.CreateModel(
            name="Appeal",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "student_full_name",
                    models.CharField(max_length=255, verbose_name="Student full name"),
                ),
                (
                    "student_phone",
                    models.CharField(
                        max_length=50,
                        validators=[appeals.models.validate_phone],
                        verbose_name="Student phone",
                    ),
                ),
                ("summary", models.CharField(max_length=255, verbose_name="Summary")),
                ("description", models.TextField(verbose_name="Description")),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("new", "New"),
                            ("in_progress", "In progress"),
                            ("closed", "Closed"),
                        ],
                        default="new",
                        max_length=20,
                        verbose_name="Status",
                    ),
                ),
                ("due_at", models.DateTimeField(verbose_name="Due at")),
                ("result", models.TextField(blank=True, verbose_name="Result")),
                (
                    "created_at",
                    models.DateTimeField(
                        default=django.utils.timezone.now, verbose_name="Created at"
                    ),
                ),
                (
                    "updated_at",
                    models.DateTimeField(auto_now=True, verbose_name="Updated at"),
                ),
                (
                    "accepted_at",
                    models.DateTimeField(blank=True, null=True, verbose_name="Accepted at"),
                ),
                (
                    "closed_at",
                    models.DateTimeField(blank=True, null=True, verbose_name="Closed at"),
                ),
                (
                    "accepted_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="accepted_appeals",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="Accepted by",
                    ),
                ),
                (
                    "created_by",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="created_appeals",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="Created by",
                    ),
                ),
                (
                    "category",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="appeals",
                        to="appeals.appealcategory",
                        verbose_name="Category",
                    ),
                ),
            ],
            options={
                "verbose_name": "Appeal",
                "verbose_name_plural": "Appeals",
                "ordering": ["-created_at", "-pk"],
            },
        ),
        migrations.CreateModel(
            name="AppealComment",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("text", models.TextField(verbose_name="Text")),
                (
                    "created_at",
                    models.DateTimeField(
                        default=django.utils.timezone.now, verbose_name="Created at"
                    ),
                ),
                (
                    "appeal",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="comments",
                        to="appeals.appeal",
                        verbose_name="Appeal",
                    ),
                ),
                (
                    "author",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="appeal_comments",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="Author",
                    ),
                ),
            ],
            options={
                "verbose_name": "Appeal comment",
                "verbose_name_plural": "Appeal comments",
                "ordering": ["created_at", "-pk"],
            },
        ),
        migrations.CreateModel(
            name="AppealHistoryEvent",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "event_type",
                    models.CharField(
                        choices=[
                            ("created", "Created"),
                            ("category_changed", "Category changed"),
                            ("department_changed", "Department changed"),
                            ("due_at_changed", "Due date changed"),
                            ("accepted", "Accepted"),
                            ("status_changed", "Status changed"),
                            ("comment_added", "Comment added"),
                            ("result_updated", "Result updated"),
                            ("closed", "Closed"),
                        ],
                        max_length=50,
                        verbose_name="Event type",
                    ),
                ),
                ("message", models.TextField(blank=True, verbose_name="Message")),
                (
                    "created_at",
                    models.DateTimeField(
                        default=django.utils.timezone.now, verbose_name="Created at"
                    ),
                ),
                (
                    "actor",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="appeal_history_events",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="Actor",
                    ),
                ),
                (
                    "appeal",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="history_events",
                        to="appeals.appeal",
                        verbose_name="Appeal",
                    ),
                ),
            ],
            options={
                "verbose_name": "Appeal history event",
                "verbose_name_plural": "Appeal history events",
                "ordering": ["created_at", "-pk"],
            },
        ),
        migrations.CreateModel(
            name="Department",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("name", models.CharField(max_length=150, verbose_name="Name")),
                (
                    "name_key",
                    models.CharField(
                        blank=True,
                        editable=False,
                        max_length=255,
                        verbose_name="Name key",
                    ),
                ),
                (
                    "description",
                    models.TextField(blank=True, verbose_name="Description"),
                ),
                (
                    "is_active",
                    models.BooleanField(default=True, verbose_name="Is active"),
                ),
                (
                    "created_at",
                    models.DateTimeField(auto_now_add=True, verbose_name="Created at"),
                ),
                (
                    "updated_at",
                    models.DateTimeField(auto_now=True, verbose_name="Updated at"),
                ),
                (
                    "members",
                    models.ManyToManyField(
                        blank=True,
                        related_name="departments",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="Members",
                    ),
                ),
            ],
            options={
                "verbose_name": "Department",
                "verbose_name_plural": "Departments",
                "ordering": ["name", "-pk"],
            },
        ),
        migrations.AddField(
            model_name="appealcategory",
            name="department",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name="categories",
                to="appeals.department",
                verbose_name="Department",
            ),
        ),
        migrations.AddField(
            model_name="appeal",
            name="department",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name="appeals",
                to="appeals.department",
                verbose_name="Department",
            ),
        ),
        migrations.AddConstraint(
            model_name="department",
            constraint=models.UniqueConstraint(
                fields=("name_key",),
                name="unique_department_name_key",
                violation_error_message="Department with this name already exists.",
            ),
        ),
        migrations.AddConstraint(
            model_name="appealcategory",
            constraint=models.UniqueConstraint(
                fields=("name_key",),
                name="unique_appeal_category_name_key",
                violation_error_message="Appeal category with this name already exists.",
            ),
        ),
    ]
