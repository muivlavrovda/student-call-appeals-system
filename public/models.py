from typing import Any

from django.db import models
from django.utils.translation import gettext_lazy as _

from appeals.models import normalize_spaces


class Feedback(models.Model):
    """Сообщение из публичной формы обратной связи.

    Хранится отдельно от заявок по телефонным звонкам и не участвует в их
    обработке: это канал связи посетителя сайта с администратором.
    """

    name = models.CharField(
        _("Name"),
        max_length=150,
    )

    email = models.EmailField(
        _("Email"),
    )

    message = models.TextField(
        _("Message"),
    )

    is_processed = models.BooleanField(
        _("Is processed"),
        default=False,
    )

    created_at = models.DateTimeField(
        _("Created at"),
        auto_now_add=True,
    )

    class Meta:
        verbose_name = _("Feedback message")
        verbose_name_plural = _("Feedback messages")
        ordering = ["-created_at", "-pk"]

    def __str__(self) -> str:
        return _("Feedback from {name}").format(name=self.name)

    def save(self, *args: Any, **kwargs: Any) -> None:
        self.name = normalize_spaces(self.name)
        self.message = self.message.strip()
        super().save(*args, **kwargs)
