from django.contrib.auth.views import LogoutView
from django.urls import path

from . import views

app_name = "accounts"

urlpatterns = [
    path("signup/", views.SignUpView.as_view(), name="signup"),
    path("login/", views.TrainingLoginView.as_view(), name="login"),
    path("logout/", LogoutView.as_view(), name="logout"),
    path("admin-panel/", views.AdminDashboardView.as_view(), name="admin_dashboard"),
    # Admin dashboard: user CRUD
    path("admin-panel/users/", views.UserListView.as_view(), name="admin_user_list"),
    path("admin-panel/users/add/", views.UserCreateView.as_view(), name="admin_user_add"),
    path("admin-panel/users/<int:pk>/edit/", views.UserUpdateView.as_view(), name="admin_user_edit"),
    path("admin-panel/users/<int:pk>/delete/", views.UserDeleteView.as_view(), name="admin_user_delete"),
]
