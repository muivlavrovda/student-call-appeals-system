from django import forms

from appeals.models import normalize_spaces
from public.models import Feedback


class BootstrapModelForm(forms.ModelForm):
    """ModelForm, помечающий поля с ошибками классом Bootstrap is-invalid.

    Класс добавляется после валидации, поэтому поле подсвечивается красной
    рамкой, а сообщения об ошибках выводятся шаблоном поля.
    """

    def is_valid(self) -> bool:
        valid = super().is_valid()
        for field_name in self.errors:
            if field_name in self.fields:
                widget = self.fields[field_name].widget
                classes = widget.attrs.get("class", "")
                if "is-invalid" not in classes.split():
                    widget.attrs["class"] = f"{classes} is-invalid".strip()
        return valid


class FeedbackForm(BootstrapModelForm):
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
                    "class": "form-control",
                    "placeholder": "Как к вам обращаться?",
                    "autocomplete": "name",
                },
            ),
            "email": forms.EmailInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "you@example.com",
                    "autocomplete": "email",
                },
            ),
            "message": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 5,
                    "placeholder": "Опишите вопрос или предложение.",
                },
            ),
        }

    def clean_name(self) -> str:
        return normalize_spaces(self.cleaned_data["name"])
