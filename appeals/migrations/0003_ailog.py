import django.db.models.deletion
import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("appeals", "0002_alter_appeal_options"),
    ]

    operations = [
        migrations.CreateModel(
            name="AILog",
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
                    "created_at",
                    models.DateTimeField(
                        default=django.utils.timezone.now, verbose_name="Created at"
                    ),
                ),
                ("model", models.CharField(max_length=100, verbose_name="Model")),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("ok", "Classified"),
                            ("undecided", "Could not decide"),
                            ("error", "Error"),
                        ],
                        max_length=20,
                        verbose_name="Status",
                    ),
                ),
                (
                    "description_in",
                    models.TextField(blank=True, verbose_name="Call description"),
                ),
                (
                    "summary_out",
                    models.CharField(
                        blank=True, max_length=255, verbose_name="Suggested summary"
                    ),
                ),
                ("reason", models.TextField(blank=True, verbose_name="Reason")),
                (
                    "prompt_tokens",
                    models.PositiveIntegerField(
                        default=0, verbose_name="Prompt tokens"
                    ),
                ),
                (
                    "cache_hit_tokens",
                    models.PositiveIntegerField(
                        default=0, verbose_name="Cache hit tokens"
                    ),
                ),
                (
                    "cache_miss_tokens",
                    models.PositiveIntegerField(
                        default=0, verbose_name="Cache miss tokens"
                    ),
                ),
                (
                    "completion_tokens",
                    models.PositiveIntegerField(
                        default=0, verbose_name="Completion tokens"
                    ),
                ),
                (
                    "cost_usd",
                    models.DecimalField(
                        decimal_places=8,
                        default=0,
                        max_digits=12,
                        verbose_name="Cost, USD",
                    ),
                ),
                (
                    "latency_ms",
                    models.PositiveIntegerField(default=0, verbose_name="Latency, ms"),
                ),
                (
                    "raw_request",
                    models.JSONField(blank=True, null=True, verbose_name="Raw request"),
                ),
                (
                    "raw_response",
                    models.JSONField(
                        blank=True, null=True, verbose_name="Raw response"
                    ),
                ),
                ("error", models.TextField(blank=True, verbose_name="Error")),
                (
                    "chosen_category",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="ai_logs",
                        to="appeals.appealcategory",
                        verbose_name="Chosen category",
                    ),
                ),
            ],
            options={
                "verbose_name": "AI call log",
                "verbose_name_plural": "AI call logs",
                "ordering": ["-created_at", "-pk"],
            },
        ),
    ]
