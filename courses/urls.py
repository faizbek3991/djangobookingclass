from django.urls import path

from . import views

app_name = "courses"

urlpatterns = [
    path("", views.CourseListView.as_view(), name="course_list"),
    # Admin dashboard: courses
    path("admin-panel/courses/", views.CourseListAdminView.as_view(), name="admin_course_list"),
    path("admin-panel/courses/add/", views.CourseCreateView.as_view(), name="admin_course_add"),
    path("admin-panel/courses/<int:pk>/edit/", views.CourseUpdateView.as_view(), name="admin_course_edit"),
    path("admin-panel/courses/<int:pk>/delete/", views.CourseDeleteView.as_view(), name="admin_course_delete"),
    # Admin dashboard: sessions
    path("admin-panel/sessions/", views.SessionListAdminView.as_view(), name="admin_session_list"),
    path("admin-panel/sessions/add/", views.SessionCreateView.as_view(), name="admin_session_add"),
    path("admin-panel/sessions/<int:pk>/edit/", views.SessionUpdateView.as_view(), name="admin_session_edit"),
    path("admin-panel/sessions/<int:pk>/delete/", views.SessionDeleteView.as_view(), name="admin_session_delete"),
    # Admin dashboard: SEO settings
    path("admin-panel/seo/", views.SEOSettingsUpdateView.as_view(), name="admin_seo_settings"),
    # Public course detail (kept last: slug is a catch-all single path segment)
    path("<slug:slug>/", views.CourseDetailView.as_view(), name="course_detail"),
]
