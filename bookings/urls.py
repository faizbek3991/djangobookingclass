from django.urls import path

from . import views

app_name = "bookings"

urlpatterns = [
    path("", views.MyBookingListView.as_view(), name="booking_list"),
    path("book/<int:session_id>/", views.CreateBookingView.as_view(), name="booking_create"),
    path("<int:pk>/pay/", views.BookingPaymentView.as_view(), name="booking_pay"),
    path("<int:pk>/reschedule/", views.BookingRescheduleView.as_view(), name="booking_reschedule"),
    path("<int:pk>/cancel/", views.BookingCancelView.as_view(), name="booking_cancel"),
    # Admin dashboard: payment verification
    path("admin-panel/payments/", views.PaymentVerificationListView.as_view(), name="admin_payment_verification_list"),
    path("admin-panel/payments/<int:pk>/approve/", views.BookingApproveView.as_view(), name="admin_booking_approve"),
    path("admin-panel/payments/<int:pk>/reject/", views.BookingRejectView.as_view(), name="admin_booking_reject"),
    path("admin-panel/payment-settings/", views.PaymentSettingsUpdateView.as_view(), name="admin_payment_settings"),
]
