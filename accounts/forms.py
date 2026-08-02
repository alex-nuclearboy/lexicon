from django import forms
from django.conf import settings
from django.contrib.auth import authenticate
from django.contrib.auth.models import AbstractBaseUser
from django.http import HttpRequest


class OwnerLoginForm(forms.Form):
    password = forms.CharField(
        label="Password",
        required=True,
        strip=False,
        widget=forms.PasswordInput(
            attrs={
                "class": "login-form__input",
                "autocomplete": "current-password",
                "autofocus": True,
                "placeholder": "Enter your password",
                "aria-required": "true",
                "aria-describedby": "password-required-note",
            }
        ),
    )

    def __init__(
        self,
        *args,
        request: HttpRequest | None = None,
        **kwargs,
    ) -> None:
        super().__init__(*args, **kwargs)

        self.request = request
        self.user_cache: AbstractBaseUser | None = None

    def clean(self) -> dict:
        cleaned_data = super().clean()
        password = cleaned_data.get("password")

        if not password:
            return cleaned_data

        self.user_cache = authenticate(
            request=self.request,
            username=settings.SITE_OWNER_USERNAME,
            password=password,
        )

        if self.user_cache is None:
            self.add_error(
                "password",
                "The password is incorrect.",
            )

        return cleaned_data

    def get_user(self) -> AbstractBaseUser | None:
        return self.user_cache
