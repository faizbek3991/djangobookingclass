from django.contrib import messages
from django.http import HttpResponse
from django.template.loader import render_to_string
from django.urls import reverse_lazy
from django.utils import timezone
from django.views.generic import CreateView, DeleteView, DetailView, ListView, UpdateView

from accounts.mixins import StaffRequiredMixin

from .forms import CourseForm, SEOSettingsForm, SessionForm
from .models import Course, Session, SiteSEOSettings


# ---- Public views ----

class CourseListView(ListView):
    model = Course
    template_name = "courses/course_list.html"
    context_object_name = "courses"
    paginate_by = 12

    def get_queryset(self):
        return Course.objects.filter(is_active=True)

    def get_context_data(self, **kwargs):
        from bookings.models import Booking

        context = super().get_context_data(**kwargs)
        context["stat_course_count"] = Course.objects.filter(is_active=True).count()
        context["stat_upcoming_sessions"] = Session.objects.filter(start_at__gte=timezone.now()).count()
        context["stat_students_trained"] = Booking.objects.filter(status=Booking.STATUS_CONFIRMED).count()
        return context


class CourseDetailView(DetailView):
    model = Course
    template_name = "courses/course_detail.html"
    context_object_name = "course"
    slug_url_kwarg = "slug"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["sessions"] = self.object.upcoming_sessions
        return context


# ---- Admin dashboard: Course CRUD ----

class CourseListAdminView(StaffRequiredMixin, ListView):
    model = Course
    template_name = "courses/admin/course_list.html"
    context_object_name = "courses"
    paginate_by = 20
    ordering = ["-created_at"]


class CourseCreateView(StaffRequiredMixin, CreateView):
    model = Course
    form_class = CourseForm
    template_name = "courses/admin/course_form.html"
    success_url = reverse_lazy("courses:admin_course_list")

    def form_valid(self, form):
        messages.success(self.request, "Course created.")
        return super().form_valid(form)


class CourseUpdateView(StaffRequiredMixin, UpdateView):
    model = Course
    form_class = CourseForm
    template_name = "courses/admin/course_form.html"
    success_url = reverse_lazy("courses:admin_course_list")

    def form_valid(self, form):
        messages.success(self.request, "Course updated.")
        return super().form_valid(form)


class CourseDeleteView(StaffRequiredMixin, DeleteView):
    model = Course
    template_name = "courses/admin/course_confirm_delete.html"
    success_url = reverse_lazy("courses:admin_course_list")

    def form_valid(self, form):
        messages.success(self.request, "Course deleted.")
        return super().form_valid(form)


# ---- Admin dashboard: Session CRUD ----

class SessionListAdminView(StaffRequiredMixin, ListView):
    model = Session
    template_name = "courses/admin/session_list.html"
    context_object_name = "sessions"
    paginate_by = 20
    ordering = ["-start_at"]


class SessionCreateView(StaffRequiredMixin, CreateView):
    model = Session
    form_class = SessionForm
    template_name = "courses/admin/session_form.html"
    success_url = reverse_lazy("courses:admin_session_list")

    def form_valid(self, form):
        messages.success(self.request, "Session created.")
        return super().form_valid(form)


class SessionUpdateView(StaffRequiredMixin, UpdateView):
    model = Session
    form_class = SessionForm
    template_name = "courses/admin/session_form.html"
    success_url = reverse_lazy("courses:admin_session_list")

    def form_valid(self, form):
        messages.success(self.request, "Session updated.")
        return super().form_valid(form)


class SessionDeleteView(StaffRequiredMixin, DeleteView):
    model = Session
    template_name = "courses/admin/session_confirm_delete.html"
    success_url = reverse_lazy("courses:admin_session_list")

    def form_valid(self, form):
        messages.success(self.request, "Session deleted.")
        return super().form_valid(form)


# ---- Admin dashboard: SEO settings ----

class SEOSettingsUpdateView(StaffRequiredMixin, UpdateView):
    model = SiteSEOSettings
    form_class = SEOSettingsForm
    template_name = "courses/admin/seo_settings_form.html"
    success_url = reverse_lazy("courses:admin_seo_settings")

    def get_object(self, queryset=None):
        return SiteSEOSettings.get_solo()

    def form_valid(self, form):
        messages.success(self.request, "SEO settings updated.")
        return super().form_valid(form)


# ---- SEO: sitemap & robots.txt ----

def sitemap_view(request):
    base = request.build_absolute_uri("/").rstrip("/")
    urls = [{"loc": f"{base}/", "changefreq": "daily", "priority": "1.0"}]
    for course in Course.objects.filter(is_active=True):
        urls.append(
            {
                "loc": f"{base}{course.get_absolute_url()}",
                "lastmod": course.updated_at.date().isoformat(),
                "changefreq": "weekly",
                "priority": "0.8",
            }
        )
    xml = render_to_string("sitemap.xml", {"urls": urls})
    return HttpResponse(xml, content_type="application/xml")


def robots_view(request):
    base = request.build_absolute_uri("/").rstrip("/")
    lines = [
        "User-agent: *",
        "Disallow: /accounts/admin-panel/",
        "Disallow: /bookings/admin-panel/",
        "Disallow: /bookings/",
        "Disallow: /admin/",
        "",
        f"Sitemap: {base}/sitemap.xml",
    ]
    return HttpResponse("\n".join(lines), content_type="text/plain")
