from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("appeals", "0001_initial"),
    ]

    operations = [
        migrations.AlterModelOptions(
            name="appeal",
            options={
                "ordering": ["-created_at", "-pk"],
                "permissions": [
                    ("start_appeal_processing", "Can start appeal processing"),
                    ("comment_appeal", "Can comment appeal"),
                    ("close_appeal", "Can close appeal"),
                    ("transfer_appeal", "Can transfer appeal"),
                ],
                "verbose_name": "Appeal",
                "verbose_name_plural": "Appeals",
            },
        ),
    ]
