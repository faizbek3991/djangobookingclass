from django.contrib.auth import login as django_login
from django.contrib.auth import logout as django_logout
from django.contrib.auth.models import User
from django.middleware.csrf import get_token
from django.shortcuts import get_object_or_404
from ninja import Router
from ninja.security import django_auth, django_auth_is_staff

from .forms import TrainingLoginForm
from .schemas import (
    AdminUserCreateIn,
    AdminUserUpdateIn,
    LoginIn,
    MessageOut,
    SignupIn,
    UserOut,
)

auth_router = Router(tags=["auth"])
admin_users_router = Router(tags=["admin: users"], auth=django_auth_is_staff)


@auth_router.get("/csrf/", auth=None, response=MessageOut)
def get_csrf_token(request):
    """Call this first (GET) so the browser receives the csrftoken cookie
    needed for the X-CSRFToken header on subsequent POST/PUT/DELETE calls."""
    get_token(request)
    return {"detail": "CSRF cookie set."}


@auth_router.post("/signup/", auth=None, response={200: UserOut, 400: MessageOut})
def signup(request, payload: SignupIn):
    if User.objects.filter(username=payload.username).exists():
        return 400, {"detail": "That username is already taken."}
    user = User.objects.create_user(
        username=payload.username,
        email=payload.email,
        password=payload.password,
        first_name=payload.first_name,
        last_name=payload.last_name,
    )
    django_login(request, user)
    return user


@auth_router.post("/login/", auth=None, response={200: UserOut, 400: MessageOut})
def api_login(request, payload: LoginIn):
    form = TrainingLoginForm(request, data={"username": payload.username, "password": payload.password})
    if not form.is_valid():
        return 400, {"detail": "; ".join(form.errors.get("__all__", ["Invalid credentials."]))}
    django_login(request, form.get_user())
    return form.get_user()


@auth_router.post("/logout/", auth=django_auth, response=MessageOut)
def api_logout(request):
    django_logout(request)
    return {"detail": "Logged out."}


@auth_router.get("/me/", auth=django_auth, response=UserOut)
def me(request):
    return request.user


# ---- Admin: user CRUD ----

@admin_users_router.get("/", response=list[UserOut])
def list_users(request):
    return list(User.objects.all().order_by("username"))


@admin_users_router.get("/{user_id}/", response=UserOut)
def get_user(request, user_id: int):
    return get_object_or_404(User, pk=user_id)


@admin_users_router.post("/", response={201: UserOut, 400: MessageOut})
def create_user(request, payload: AdminUserCreateIn):
    if User.objects.filter(username=payload.username).exists():
        return 400, {"detail": "That username is already taken."}
    user = User.objects.create_user(
        username=payload.username,
        email=payload.email,
        password=payload.password,
        first_name=payload.first_name,
        last_name=payload.last_name,
        is_staff=payload.is_staff,
        is_active=payload.is_active,
    )
    return 201, user


@admin_users_router.put("/{user_id}/", response=UserOut)
def update_user(request, user_id: int, payload: AdminUserUpdateIn):
    user = get_object_or_404(User, pk=user_id)
    user.username = payload.username
    user.email = payload.email
    user.first_name = payload.first_name
    user.last_name = payload.last_name
    user.is_staff = payload.is_staff
    user.is_active = payload.is_active
    user.save()
    return user


@admin_users_router.delete("/{user_id}/", response=MessageOut)
def delete_user(request, user_id: int):
    user = get_object_or_404(User, pk=user_id)
    user.delete()
    return {"detail": "User deleted."}
