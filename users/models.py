from typing import Any

from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils.translation import gettext_lazy as _

from users.managers import EmailUserManager


class User(AbstractUser):
    username = None

    email = models.EmailField(
        verbose_name=_("Email"),
        unique=True,
    )

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    objects = EmailUserManager()

    class Meta(AbstractUser.Meta):
        verbose_name = _("User")
        verbose_name_plural = _("Users")
        ordering = ["-date_joined", "id"]

    def save(self, *args: Any, **kwargs: Any) -> None:
        self.email = EmailUserManager.normalize_email(self.email)
        super().save(*args, **kwargs)
