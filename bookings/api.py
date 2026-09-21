from asgiref.sync import sync_to_async
from django.shortcuts import aget_object_or_404
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


def _booking_qs():
    """Booking.session and Booking.session.course are always select_related — BookingOut's
    resolvers read them directly, so this avoids a sync lazy-load during response serialization
    (which would raise SynchronousOnlyOperation in these async views)."""
    return Booking.objects.select_related("session", "session__course")


# ---- Authenticated: payment info shown on the pay page ----
# NOTE: registered before "/{booking_id}/" below — django-ninja matches path
# operations in registration order and does not restrict {booking_id} to
# digits at the routing layer, so a literal sibling path must come first or
# it gets shadowed by the dynamic one (and then fails Pydantic int parsing).

@bookings_router.get("/payment-settings/", response=PaymentSettingsOut)
async def get_payment_settings(request):
    return await PaymentSettings.aget_solo()


# ---- User: my bookings ----

@bookings_router.get("/", response=list[BookingOut])
async def list_my_bookings(request):
    return [b async for b in _booking_qs().filter(user=request.auth)]


@bookings_router.post("/", response={201: BookingOut, 400: MessageOut})
async def create_booking(request, payload: BookingCreateIn):
    session = await aget_object_or_404(Session.objects.select_related("course"), pk=payload.session_id)

    if session.is_past:
        return 400, {"detail": "This session has already taken place."}

    existing = await _booking_qs().filter(
        user=request.auth, session=session, status__in=ACTIVE_BOOKING_STATUSES
    ).afirst()
    if existing:
        return 400, {"detail": "You already have an active booking for this session.", "booking_id": existing.pk}

    booked_count = await session.bookings.filter(status__in=ACTIVE_BOOKING_STATUSES).acount()
    if booked_count >= session.capacity:
        return 400, {"detail": "Sorry, this session is fully booked."}

    booking = await Booking.objects.acreate(user=request.auth, session=session, amount_due=session.course.price)
    return 201, booking


@bookings_router.get("/{booking_id}/", response=BookingOut)
async def get_my_booking(request, booking_id: int):
    return await aget_object_or_404(_booking_qs(), pk=booking_id, user=request.auth)


@bookings_router.post("/{booking_id}/submit-payment/", response={200: BookingOut, 400: MessageOut})
async def submit_payment(request, booking_id: int):
    booking = await aget_object_or_404(_booking_qs(), pk=booking_id, user=request.auth)
    if booking.status != Booking.STATUS_PENDING_PAYMENT:
        return 400, {"detail": "This booking isn't awaiting payment."}
    booking.status = Booking.STATUS_AWAITING_VERIFICATION
    booking.submitted_at = timezone.now()
    await booking.asave()
    return booking


@bookings_router.put("/{booking_id}/reschedule/", response={200: BookingOut, 400: MessageOut})
async def reschedule_booking(request, booking_id: int, payload: BookingRescheduleIn):
    booking = await aget_object_or_404(
        _booking_qs(), pk=booking_id, user=request.auth, status=Booking.STATUS_CONFIRMED
    )
    new_session = await aget_object_or_404(
        Session.objects.select_related("course"), pk=payload.session_id, course=booking.session.course
    )
    if new_session != booking.session:
        new_booked_count = await new_session.bookings.filter(status__in=ACTIVE_BOOKING_STATUSES).acount()
        if new_booked_count >= new_session.capacity:
            return 400, {"detail": "That session is already full."}
    if new_session.start_at < booking.session.start_at:
        return 400, {"detail": "You can only reschedule to a session on or after the current one."}
    booking.session = new_session
    await booking.asave()
    return booking


@bookings_router.delete("/{booking_id}/", response=MessageOut)
async def cancel_booking(request, booking_id: int):
    booking = await aget_object_or_404(Booking, pk=booking_id, user=request.auth)
    booking.status = Booking.STATUS_CANCELLED
    await booking.asave()
    return {"detail": "Booking cancelled."}


# ---- Admin: payment verification ----

@admin_payments_router.get("/", response=list[BookingOut])
async def admin_list_pending_payments(request):
    qs = _booking_qs().filter(status=Booking.STATUS_AWAITING_VERIFICATION).order_by("submitted_at")
    return [b async for b in qs]


@admin_payments_router.post("/{booking_id}/approve/", response={200: BookingOut, 400: MessageOut})
async def admin_approve_payment(request, booking_id: int):
    booking = await aget_object_or_404(_booking_qs(), pk=booking_id, status=Booking.STATUS_AWAITING_VERIFICATION)
    booking.status = Booking.STATUS_CONFIRMED
    booking.paid_at = timezone.now()
    await booking.asave()
    await sync_to_async(send_booking_approved_email)(booking)
    return booking


@admin_payments_router.post("/{booking_id}/reject/", response={200: BookingOut, 400: MessageOut})
async def admin_reject_payment(request, booking_id: int):
    booking = await aget_object_or_404(_booking_qs(), pk=booking_id, status=Booking.STATUS_AWAITING_VERIFICATION)
    booking.status = Booking.STATUS_PENDING_PAYMENT
    booking.submitted_at = None
    await booking.asave()
    return booking


# ---- Admin: payment settings (bank/QR) ----

@admin_payment_settings_router.get("/", response=PaymentSettingsOut)
async def admin_get_payment_settings(request):
    return await PaymentSettings.aget_solo()


@admin_payment_settings_router.put("/", response=PaymentSettingsOut)
async def admin_update_payment_settings(request, payload: PaymentSettingsIn):
    settings_obj = await PaymentSettings.aget_solo()
    for field, value in payload.dict().items():
        setattr(settings_obj, field, value)
    await settings_obj.asave()
    return settings_obj


@admin_payment_settings_router.post("/image/", response=PaymentSettingsOut)
async def admin_set_payment_qr_image(request, image: UploadedFile = File(...)):
    settings_obj = await PaymentSettings.aget_solo()
    settings_obj.qr_image = image
    await settings_obj.asave()
    return settings_obj
