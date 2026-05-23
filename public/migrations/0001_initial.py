from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="Feedback",
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
                ("email", models.EmailField(max_length=254, verbose_name="Email")),
                ("message", models.TextField(verbose_name="Message")),
                (
                    "is_processed",
                    models.BooleanField(default=False, verbose_name="Is processed"),
                ),
                (
                    "created_at",
                    models.DateTimeField(auto_now_add=True, verbose_name="Created at"),
                ),
            ],
            options={
                "verbose_name": "Feedback message",
                "verbose_name_plural": "Feedback messages",
                "ordering": ["-created_at", "-pk"],
            },
        ),
    ]
