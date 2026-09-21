from django.contrib.auth.backends import ModelBackend
from django.contrib.auth.models import User


class EmailOrUsernameModelBackend(ModelBackend):
    """Lets users log in with either their username or their email address."""

    def authenticate(self, request, username=None, password=None, **kwargs):
        if username is None:
            username = kwargs.get(User.USERNAME_FIELD)
        if username is None or password is None:
            return None

        user = (
            User.objects.filter(username__iexact=username).first()
            or User.objects.filter(email__iexact=username).first()
        )
        if user is not None and user.check_password(password) and self.user_can_authenticate(user):
            return user
        return None
