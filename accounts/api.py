from asgiref.sync import sync_to_async
from django.contrib.auth import alogin, alogout
from django.contrib.auth.models import User
from django.middleware.csrf import get_token
from django.shortcuts import aget_object_or_404
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
async def signup(request, payload: SignupIn):
    if await User.objects.filter(username=payload.username).aexists():
        return 400, {"detail": "That username is already taken."}
    user = await User.objects.acreate_user(
        username=payload.username,
        email=payload.email,
        password=payload.password,
        first_name=payload.first_name,
        last_name=payload.last_name,
    )
    await alogin(request, user, backend="django.contrib.auth.backends.ModelBackend")
    return user


@auth_router.post("/login/", auth=None, response={200: UserOut, 400: MessageOut})
async def api_login(request, payload: LoginIn):
    # AuthenticationForm (and our lockout logic in it) is sync-only, like all
    # Django Forms — run it in a worker thread rather than reimplementing the
    # lockout check here a second time.
    form = TrainingLoginForm(request, data={"username": payload.username, "password": payload.password})
    is_valid = await sync_to_async(form.is_valid)()
    if not is_valid:
        return 400, {"detail": "; ".join(form.errors.get("__all__", ["Invalid credentials."]))}
    user = form.get_user()
    await alogin(request, user)
    return user


@auth_router.post("/logout/", auth=django_auth, response=MessageOut)
async def api_logout(request):
    await alogout(request)
    return {"detail": "Logged out."}


@auth_router.get("/me/", auth=django_auth, response=UserOut)
async def me(request):
    # request.auth is the User instance django_auth already resolved for this
    # request — reusing it avoids a second, redundant user lookup.
    return request.auth


# ---- Admin: user CRUD ----

@admin_users_router.get("/", response=list[UserOut])
async def list_users(request):
    return [u async for u in User.objects.all().order_by("username")]


@admin_users_router.get("/{user_id}/", response=UserOut)
async def get_user(request, user_id: int):
    return await aget_object_or_404(User, pk=user_id)


@admin_users_router.post("/", response={201: UserOut, 400: MessageOut})
async def create_user(request, payload: AdminUserCreateIn):
    if await User.objects.filter(username=payload.username).aexists():
        return 400, {"detail": "That username is already taken."}
    user = await User.objects.acreate_user(
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
async def update_user(request, user_id: int, payload: AdminUserUpdateIn):
    user = await aget_object_or_404(User, pk=user_id)
    user.username = payload.username
    user.email = payload.email
    user.first_name = payload.first_name
    user.last_name = payload.last_name
    user.is_staff = payload.is_staff
    user.is_active = payload.is_active
    await user.asave()
    return user


@admin_users_router.delete("/{user_id}/", response=MessageOut)
async def delete_user(request, user_id: int):
    user = await aget_object_or_404(User, pk=user_id)
    await user.adelete()
    return {"detail": "User deleted."}
