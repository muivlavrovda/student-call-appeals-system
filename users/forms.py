from django.contrib.auth.forms import AuthenticationForm

from core.forms import BootstrapFormMixin


class LoginForm(BootstrapFormMixin, AuthenticationForm):
    """Форма входа по электронной почте с русскими подписями и сообщениями."""

    error_messages = {
        **AuthenticationForm.error_messages,
        "invalid_login": "Неверный адрес электронной почты или пароль.",
        "inactive": "Эта учетная запись отключена.",
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["username"].label = "Электронная почта"
        self.fields["username"].widget.attrs.update(
            {
                "autocomplete": "email",
                "autofocus": True,
            }
        )
        self.fields["password"].label = "Пароль"
        self.fields["password"].widget.attrs.update(
            {
                "autocomplete": "current-password",
            }
        )
