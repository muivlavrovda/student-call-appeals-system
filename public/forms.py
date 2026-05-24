from django import forms

from appeals.models import normalize_spaces
from core.forms import BootstrapFormMixin
from public.models import Feedback


class FeedbackForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = Feedback
        fields = ["name", "email", "message"]
        labels = {
            "name": "Ваше имя",
            "email": "Электронная почта",
            "message": "Сообщение",
        }
        error_messages = {
            "name": {"required": "Укажите, как к вам обращаться."},
            "email": {
                "required": "Укажите электронную почту.",
                "invalid": "Введите корректный адрес электронной почты.",
            },
            "message": {"required": "Введите сообщение."},
        }
        widgets = {
            "name": forms.TextInput(
                attrs={
                    "placeholder": "Как к вам обращаться?",
                    "autocomplete": "name",
                },
            ),
            "email": forms.EmailInput(
                attrs={
                    "placeholder": "you@example.com",
                    "autocomplete": "email",
                },
            ),
            "message": forms.Textarea(
                attrs={
                    "rows": 5,
                    "placeholder": "Опишите вопрос или предложение.",
                },
            ),
        }

    def clean_name(self) -> str:
        return normalize_spaces(self.cleaned_data["name"])
