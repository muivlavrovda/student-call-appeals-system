from os import getenv
from typing import Any

from django.core.management.base import BaseCommand

from users.models import User


class Command(BaseCommand):
    help = "Create an admin user from DJ_DEFAULT_ADMIN env var if it doesn't exist."

    def handle(self, *args: Any, **options: Any) -> None:
        env_value = getenv("DJ_DEFAULT_ADMIN", "")
        if not env_value:
            self.stdout.write(
                self.style.WARNING("DJ_DEFAULT_ADMIN is not set; skipping admin creation.")
            )
            return

        try:
            email, password = env_value.split("|", 1)
        except ValueError:
            self.stdout.write(
                self.style.WARNING("DJ_DEFAULT_ADMIN must be formatted as 'email|password'.")
            )
            return

        email = User.objects.normalize_email(email)
        if User.objects.filter(email=email).exists():
            self.stdout.write(self.style.NOTICE(f"Admin user {email!r} already exists; skipping."))
            return

        User.objects.create_superuser(email=email, password=password)
        self.stdout.write(self.style.SUCCESS(f"Admin user {email!r} created."))
