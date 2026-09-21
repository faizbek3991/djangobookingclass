from ninja import NinjaAPI

from accounts.api import admin_users_router, auth_router
from bookings.api import admin_payment_settings_router, admin_payments_router, bookings_router
from courses.api import admin_courses_router, admin_seo_router, admin_sessions_router, public_router

api = NinjaAPI(
    title="TrainBook API",
    version="1.0.0",
    description=(
        "REST API for the TrainBook training-booking app. "
        "Authentication is Django session-cookie based: call GET /api/auth/csrf/ first, "
        "log in via POST /api/auth/login/, then send the csrftoken cookie's value back as an "
        "X-CSRFToken header on every POST/PUT/DELETE request."
    ),
)

# Public + user-facing
api.add_router("/auth/", auth_router)
api.add_router("/courses/", public_router)
api.add_router("/bookings/", bookings_router)

# Staff-only (admin dashboard equivalents)
api.add_router("/admin/users/", admin_users_router)
api.add_router("/admin/courses/", admin_courses_router)
api.add_router("/admin/sessions/", admin_sessions_router)
api.add_router("/admin/seo/", admin_seo_router)
api.add_router("/admin/payments/", admin_payments_router)
api.add_router("/admin/payment-settings/", admin_payment_settings_router)
