from django.conf import settings
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.contrib.auth.models import User
from django.core.cache import cache
from django import forms

TEXT_INPUT_CLASS = "form-control"
CHECKBOX_CLASS = "form-check-input"


def _client_ip(request):
    return request.META.get("REMOTE_ADDR", "unknown")


def _lockout_cache_key(request, username):
    return f"login_attempts:{_client_ip(request)}:{username.lower()}"


class TrainingLoginForm(AuthenticationForm):
    """Adds a per-IP+username lockout on top of Django's default login form."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            field.widget.attrs.setdefault("class", TEXT_INPUT_CLASS)

    def clean(self):
        username = self.cleaned_data.get("username")
        request = self.request

        if username and request:
            key = _lockout_cache_key(request, username)
            if cache.get(key, 0) >= settings.LOGIN_ATTEMPT_LIMIT:
                raise forms.ValidationError(
                    "Too many failed login attempts for this account. "
                    "Please try again in %(minutes)d minutes."
                    % {"minutes": settings.LOGIN_ATTEMPT_LOCKOUT_MINUTES},
                    code="locked_out",
                )

        try:
            cleaned_data = super().clean()
        except forms.ValidationError:
            if username and request:
                key = _lockout_cache_key(request, username)
                cache.set(key, cache.get(key, 0) + 1, timeout=settings.LOGIN_ATTEMPT_LOCKOUT_MINUTES * 60)
            raise
        else:
            if username and request:
                cache.delete(_lockout_cache_key(request, username))
            return cleaned_data


class SignUpForm(UserCreationForm):
    email = forms.EmailField(required=True)

    class Meta:
        model = User
        fields = ["username", "first_name", "last_name", "email", "password1", "password2"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            field.widget.attrs.setdefault("class", TEXT_INPUT_CLASS)


class AdminUserCreateForm(UserCreationForm):
    email = forms.EmailField(required=True)

    class Meta:
        model = User
        fields = ["username", "first_name", "last_name", "email", "is_staff", "is_active", "password1", "password2"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            if isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs.setdefault("class", CHECKBOX_CLASS)
            else:
                field.widget.attrs.setdefault("class", TEXT_INPUT_CLASS)


class AdminUserUpdateForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ["username", "first_name", "last_name", "email", "is_staff", "is_active"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            if isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs.setdefault("class", CHECKBOX_CLASS)
            else:
                field.widget.attrs.setdefault("class", TEXT_INPUT_CLASS)
