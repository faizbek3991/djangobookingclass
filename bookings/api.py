from django.shortcuts import get_object_or_404
from django.utils import timezone
from ninja import File, Router
from ninja.files import UploadedFile
from ninja.security import django_auth, django_auth_is_staff

from courses.models import Session

from .emails import send_booking_approved_email
from .models import ACTIVE_BOOKING_STATUSES, Booking, PaymentSettings
from .schemas import (
    BookingCreateIn,
    BookingOut,
    BookingRescheduleIn,
    MessageOut,
    PaymentSettingsIn,
    PaymentSettingsOut,
)

bookings_router = Router(tags=["bookings"], auth=django_auth)
admin_payments_router = Router(tags=["admin: payments"], auth=django_auth_is_staff)
admin_payment_settings_router = Router(tags=["admin: payment settings"], auth=django_auth_is_staff)


# ---- Authenticated: payment info shown on the pay page ----
# NOTE: registered before "/{booking_id}/" below — django-ninja matches path
# operations in registration order and does not restrict {booking_id} to
# digits at the routing layer, so a literal sibling path must come first or
# it gets shadowed by the dynamic one (and then fails Pydantic int parsing).

@bookings_router.get("/payment-settings/", response=PaymentSettingsOut)
def get_payment_settings(request):
    return PaymentSettings.get_solo()


# ---- User: my bookings ----

@bookings_router.get("/", response=list[BookingOut])
def list_my_bookings(request):
    return list(
        Booking.objects.filter(user=request.user).select_related("session", "session__course")
    )


@bookings_router.post("/", response={201: BookingOut, 400: MessageOut})
def create_booking(request, payload: BookingCreateIn):
    session = get_object_or_404(Session, pk=payload.session_id)

    if session.is_past:
        return 400, {"detail": "This session has already taken place."}

    existing = Booking.objects.filter(
        user=request.user, session=session, status__in=ACTIVE_BOOKING_STATUSES
    ).first()
    if existing:
        return 400, {"detail": "You already have an active booking for this session.", "booking_id": existing.pk}

    if session.is_full:
        return 400, {"detail": "Sorry, this session is fully booked."}

    booking = Booking.objects.create(user=request.user, session=session, amount_due=session.course.price)
    return 201, booking


@bookings_router.get("/{booking_id}/", response=BookingOut)
def get_my_booking(request, booking_id: int):
    return get_object_or_404(Booking, pk=booking_id, user=request.user)


@bookings_router.post("/{booking_id}/submit-payment/", response={200: BookingOut, 400: MessageOut})
def submit_payment(request, booking_id: int):
    booking = get_object_or_404(Booking, pk=booking_id, user=request.user)
    if booking.status != Booking.STATUS_PENDING_PAYMENT:
        return 400, {"detail": "This booking isn't awaiting payment."}
    booking.status = Booking.STATUS_AWAITING_VERIFICATION
    booking.submitted_at = timezone.now()
    booking.save()
    return booking


@bookings_router.put("/{booking_id}/reschedule/", response={200: BookingOut, 400: MessageOut})
def reschedule_booking(request, booking_id: int, payload: BookingRescheduleIn):
    booking = get_object_or_404(Booking, pk=booking_id, user=request.user, status=Booking.STATUS_CONFIRMED)
    new_session = get_object_or_404(Session, pk=payload.session_id, course=booking.session.course)
    if new_session != booking.session and new_session.is_full:
        return 400, {"detail": "That session is already full."}
    if new_session.start_at < booking.session.start_at:
        return 400, {"detail": "You can only reschedule to a session on or after the current one."}
    booking.session = new_session
    booking.save()
    return booking


@bookings_router.delete("/{booking_id}/", response=MessageOut)
def cancel_booking(request, booking_id: int):
    booking = get_object_or_404(Booking, pk=booking_id, user=request.user)
    booking.status = Booking.STATUS_CANCELLED
    booking.save()
    return {"detail": "Booking cancelled."}


# ---- Admin: payment verification ----

@admin_payments_router.get("/", response=list[BookingOut])
def admin_list_pending_payments(request):
    return list(
        Booking.objects.filter(status=Booking.STATUS_AWAITING_VERIFICATION)
        .select_related("user", "session", "session__course")
        .order_by("submitted_at")
    )


@admin_payments_router.post("/{booking_id}/approve/", response={200: BookingOut, 400: MessageOut})
def admin_approve_payment(request, booking_id: int):
    booking = get_object_or_404(Booking, pk=booking_id, status=Booking.STATUS_AWAITING_VERIFICATION)
    booking.status = Booking.STATUS_CONFIRMED
    booking.paid_at = timezone.now()
    booking.save()
    send_booking_approved_email(booking)
    return booking


@admin_payments_router.post("/{booking_id}/reject/", response={200: BookingOut, 400: MessageOut})
def admin_reject_payment(request, booking_id: int):
    booking = get_object_or_404(Booking, pk=booking_id, status=Booking.STATUS_AWAITING_VERIFICATION)
    booking.status = Booking.STATUS_PENDING_PAYMENT
    booking.submitted_at = None
    booking.save()
    return booking


# ---- Admin: payment settings (bank/QR) ----

@admin_payment_settings_router.get("/", response=PaymentSettingsOut)
def admin_get_payment_settings(request):
    return PaymentSettings.get_solo()


@admin_payment_settings_router.put("/", response=PaymentSettingsOut)
def admin_update_payment_settings(request, payload: PaymentSettingsIn):
    settings_obj = PaymentSettings.get_solo()
    for field, value in payload.dict().items():
        setattr(settings_obj, field, value)
    settings_obj.save()
    return settings_obj


@admin_payment_settings_router.post("/image/", response=PaymentSettingsOut)
def admin_set_payment_qr_image(request, image: UploadedFile = File(...)):
    settings_obj = PaymentSettings.get_solo()
    settings_obj.qr_image = image
    settings_obj.save()
    return settings_obj
