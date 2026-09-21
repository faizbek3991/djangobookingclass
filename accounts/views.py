from django.contrib.auth import login
from django.contrib.auth.models import User
from django.contrib import messages
from django.contrib.auth.views import LoginView
from django.db.models import Count, Sum
from django.urls import reverse_lazy
from django.utils import timezone
from django.views.generic import CreateView, DeleteView, ListView, TemplateView, UpdateView

from bookings.models import Booking
from courses.models import Course, Session

from .forms import AdminUserCreateForm, AdminUserUpdateForm, SignUpForm, TrainingLoginForm
from .mixins import StaffRequiredMixin


class AdminDashboardView(StaffRequiredMixin, TemplateView):
    template_name = "accounts/admin/dashboard.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["course_count"] = Course.objects.count()
        context["session_count"] = Session.objects.count()
        context["user_count"] = User.objects.count()
        confirmed_bookings = Booking.objects.filter(status=Booking.STATUS_CONFIRMED)
        context["booking_count"] = confirmed_bookings.count()
        context["total_sales"] = confirmed_bookings.aggregate(total=Sum("amount_due"))["total"] or 0
        context["pending_verification_count"] = Booking.objects.filter(
            status=Booking.STATUS_AWAITING_VERIFICATION
        ).count()

        # Booking status breakdown
        status_counts = dict(
            Booking.objects.values_list("status").annotate(count=Count("id"))
        )
        total_bookings = sum(status_counts.values())
        context["status_breakdown"] = [
            {
                "value": value,
                "label": label,
                "count": status_counts.get(value, 0),
                "percent": round(status_counts.get(value, 0) / total_bookings * 100) if total_bookings else 0,
            }
            for value, label in Booking.STATUS_CHOICES
        ]

        # Top courses by confirmed revenue
        context["top_courses"] = (
            Booking.objects.filter(status=Booking.STATUS_CONFIRMED)
            .values("session__course__id", "session__course__title")
            .annotate(revenue=Sum("amount_due"), bookings=Count("id"))
            .order_by("-revenue")[:5]
        )

        # Sessions in the next 14 days
        now = timezone.now()
        context["upcoming_sessions"] = (
            Session.objects.filter(start_at__gte=now, start_at__lte=now + timezone.timedelta(days=14))
            .select_related("course")
            .order_by("start_at")
        )
        return context


class SignUpView(CreateView):
    model = User
    form_class = SignUpForm
    template_name = "accounts/signup.html"
    success_url = reverse_lazy("courses:course_list")

    def form_valid(self, form):
        response = super().form_valid(form)
        login(self.request, self.object, backend="django.contrib.auth.backends.ModelBackend")
        messages.success(self.request, "Welcome! Your account has been created.")
        return response


class TrainingLoginView(LoginView):
    template_name = "accounts/login.html"
    authentication_form = TrainingLoginForm


# ---- Admin dashboard: User CRUD ----

class UserListView(StaffRequiredMixin, ListView):
    model = User
    template_name = "accounts/admin/user_list.html"
    context_object_name = "users"
    paginate_by = 20
    ordering = ["username"]


class UserCreateView(StaffRequiredMixin, CreateView):
    model = User
    form_class = AdminUserCreateForm
    template_name = "accounts/admin/user_form.html"
    success_url = reverse_lazy("accounts:admin_user_list")

    def form_valid(self, form):
        messages.success(self.request, "User created.")
        return super().form_valid(form)


class UserUpdateView(StaffRequiredMixin, UpdateView):
    model = User
    form_class = AdminUserUpdateForm
    template_name = "accounts/admin/user_form.html"
    success_url = reverse_lazy("accounts:admin_user_list")

    def form_valid(self, form):
        messages.success(self.request, "User updated.")
        return super().form_valid(form)


class UserDeleteView(StaffRequiredMixin, DeleteView):
    model = User
    template_name = "accounts/admin/user_confirm_delete.html"
    success_url = reverse_lazy("accounts:admin_user_list")

    def form_valid(self, form):
        messages.success(self.request, "User deleted.")
        return super().form_valid(form)
