from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.utils import timezone
from django.views import View
from django.views.generic import DeleteView, DetailView, ListView, UpdateView

from accounts.mixins import StaffRequiredMixin
from courses.models import Session

from .certificates import build_certificate_pdf, certificate_eligible, certificate_id
from .emails import send_booking_approved_email
from .forms import BookingCertificateForm, BookingRescheduleForm, CertificateSettingsForm, PaymentSettingsForm
from .models import ACTIVE_BOOKING_STATUSES, Booking, CertificateSettings, PaymentSettings


class MyBookingListView(LoginRequiredMixin, ListView):
    model = Booking
    template_name = "bookings/booking_list.html"
    context_object_name = "bookings"

    def get_queryset(self):
        return Booking.objects.filter(user=self.request.user).select_related("session", "session__course")

    def get_context_data(self, **kwargs):
        return super().get_context_data(now=timezone.now(), **kwargs)


class CreateBookingView(LoginRequiredMixin, View):
    """Books a seat in a session, then sends the user to the payment page."""

    def post(self, request, session_id):
        session = get_object_or_404(Session, pk=session_id)

        if session.is_past:
            messages.error(request, "This session has already taken place.")
            return redirect(session.course.get_absolute_url())

        existing = Booking.objects.filter(
            user=request.user, session=session, status__in=ACTIVE_BOOKING_STATUSES
        ).first()
        if existing:
            messages.info(request, "You already booked this session.")
            return redirect("bookings:booking_pay", pk=existing.pk)

        if session.is_full:
            messages.error(request, "Sorry, this session is fully booked.")
            return redirect(session.course.get_absolute_url())

        booking = Booking.objects.create(
            user=request.user,
            session=session,
            amount_due=session.course.price,
        )
        return redirect("bookings:booking_pay", pk=booking.pk)


class BookingPaymentView(LoginRequiredMixin, DetailView):
    """Shows the bank QR code / details, and lets the user mark payment as made."""

    model = Booking
    template_name = "bookings/booking_pay.html"
    context_object_name = "booking"

    def get_queryset(self):
        return Booking.objects.filter(user=self.request.user)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["payment_settings"] = PaymentSettings.get_solo()
        return context

    def post(self, request, *args, **kwargs):
        booking = self.get_object()
        if booking.status == Booking.STATUS_PENDING_PAYMENT:
            booking.status = Booking.STATUS_AWAITING_VERIFICATION
            booking.submitted_at = timezone.now()
            booking.save()
            messages.success(
                request,
                "Thanks! We'll verify your payment and confirm your seat shortly.",
            )
        return redirect("bookings:booking_pay", pk=booking.pk)


class BookingRescheduleView(LoginRequiredMixin, UpdateView):
    model = Booking
    form_class = BookingRescheduleForm
    template_name = "bookings/booking_form.html"
    success_url = reverse_lazy("bookings:booking_list")

    def get_queryset(self):
        return Booking.objects.filter(user=self.request.user, status=Booking.STATUS_CONFIRMED)

    def form_valid(self, form):
        messages.success(self.request, "Booking updated to the new session.")
        return super().form_valid(form)


class BookingCancelView(LoginRequiredMixin, DeleteView):
    model = Booking
    template_name = "bookings/booking_confirm_cancel.html"
    success_url = reverse_lazy("bookings:booking_list")

    def get_queryset(self):
        return Booking.objects.filter(user=self.request.user)

    def form_valid(self, form):
        self.object = self.get_object()
        self.object.status = Booking.STATUS_CANCELLED
        self.object.save()
        messages.success(self.request, "Booking cancelled.")
        return redirect(self.success_url)


# ---- Admin dashboard: payment verification ----

class PaymentVerificationListView(StaffRequiredMixin, ListView):
    model = Booking
    template_name = "bookings/admin/payment_verification_list.html"
    context_object_name = "bookings"
    paginate_by = 20

    def get_queryset(self):
        return Booking.objects.filter(
            status=Booking.STATUS_AWAITING_VERIFICATION
        ).select_related("user", "session", "session__course").order_by("submitted_at")


class BookingApproveView(StaffRequiredMixin, View):
    def post(self, request, pk):
        booking = get_object_or_404(Booking, pk=pk, status=Booking.STATUS_AWAITING_VERIFICATION)
        booking.status = Booking.STATUS_CONFIRMED
        booking.paid_at = timezone.now()
        booking.save()
        send_booking_approved_email(booking)
        messages.success(request, f"Booking approved — meeting link emailed to {booking.user.email}.")
        return redirect("bookings:admin_payment_verification_list")


class BookingRejectView(StaffRequiredMixin, View):
    def post(self, request, pk):
        booking = get_object_or_404(Booking, pk=pk, status=Booking.STATUS_AWAITING_VERIFICATION)
        booking.status = Booking.STATUS_PENDING_PAYMENT
        booking.submitted_at = None
        booking.save()
        messages.warning(request, "Payment rejected — the user can submit payment again.")
        return redirect("bookings:admin_payment_verification_list")


class PaymentSettingsUpdateView(StaffRequiredMixin, UpdateView):
    model = PaymentSettings
    form_class = PaymentSettingsForm
    template_name = "bookings/admin/payment_settings_form.html"
    success_url = reverse_lazy("bookings:admin_payment_settings")

    def get_object(self, queryset=None):
        return PaymentSettings.get_solo()

    def form_valid(self, form):
        messages.success(self.request, "Payment settings updated.")
        return super().form_valid(form)


# ---- Certificates ----

class CertificateDownloadView(LoginRequiredMixin, View):
    """Downloads the PDF certificate for a confirmed booking whose session has ended.
    Owners can download their own; staff can download any."""

    def get(self, request, pk):
        from django.http import FileResponse, Http404

        qs = Booking.objects.select_related("user", "session", "session__course")
        if not request.user.is_staff:
            qs = qs.filter(user=request.user)
        booking = get_object_or_404(qs, pk=pk)
        if not certificate_eligible(booking):
            raise Http404("Certificate not available yet.")
        filename = f"sijil-{certificate_id(booking)}.pdf"
        return FileResponse(build_certificate_pdf(booking), as_attachment=True, filename=filename,
                            content_type="application/pdf")


class AdminCertificateListView(StaffRequiredMixin, ListView):
    template_name = "bookings/admin/certificate_list.html"
    context_object_name = "bookings"
    paginate_by = 30

    def get_queryset(self):
        return (Booking.objects.filter(status=Booking.STATUS_CONFIRMED, session__end_at__lte=timezone.now())
                .select_related("user", "session", "session__course").order_by("-session__end_at"))


class CertificateSettingsUpdateView(StaffRequiredMixin, UpdateView):
    model = CertificateSettings
    form_class = CertificateSettingsForm
    template_name = "bookings/admin/certificate_settings_form.html"
    success_url = reverse_lazy("bookings:admin_certificate_settings")

    def get_object(self, queryset=None):
        return CertificateSettings.get_solo()

    def form_valid(self, form):
        messages.success(self.request, "Certificate template updated.")
        return super().form_valid(form)


class BookingCertificateUpdateView(StaffRequiredMixin, UpdateView):
    model = Booking
    form_class = BookingCertificateForm
    template_name = "bookings/admin/certificate_booking_form.html"
    success_url = reverse_lazy("bookings:admin_certificate_list")

    def get_queryset(self):
        return Booking.objects.select_related("user", "session", "session__course")

    def form_valid(self, form):
        messages.success(self.request, "Certificate details updated.")
        return super().form_valid(form)
