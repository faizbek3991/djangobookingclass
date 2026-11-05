from django.conf import settings
from django.db import models

from courses.models import Session

ACTIVE_BOOKING_STATUSES = ["pending_payment", "awaiting_verification", "confirmed"]


class Booking(models.Model):
    STATUS_PENDING_PAYMENT = "pending_payment"
    STATUS_AWAITING_VERIFICATION = "awaiting_verification"
    STATUS_CONFIRMED = "confirmed"
    STATUS_CANCELLED = "cancelled"
    STATUS_CHOICES = [
        (STATUS_PENDING_PAYMENT, "Pending payment"),
        (STATUS_AWAITING_VERIFICATION, "Awaiting verification"),
        (STATUS_CONFIRMED, "Confirmed"),
        (STATUS_CANCELLED, "Cancelled"),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="bookings")
    session = models.ForeignKey(Session, on_delete=models.CASCADE, related_name="bookings")
    status = models.CharField(max_length=25, choices=STATUS_CHOICES, default=STATUS_PENDING_PAYMENT)
    amount_due = models.DecimalField(max_digits=8, decimal_places=2)
    booked_at = models.DateTimeField(auto_now_add=True)
    submitted_at = models.DateTimeField(null=True, blank=True, help_text="When the user marked payment as made")
    paid_at = models.DateTimeField(null=True, blank=True, help_text="When admin approved the payment")

    # Per-certificate overrides. Blank means "use the session/user data".
    cert_name = models.CharField("Certificate name", max_length=150, blank=True, default="")
    cert_course_title = models.CharField("Certificate course title", max_length=200, blank=True, default="")
    cert_date = models.DateField("Certificate session date", null=True, blank=True)

    class Meta:
        ordering = ["-booked_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["user", "session"],
                condition=models.Q(status__in=ACTIVE_BOOKING_STATUSES),
                name="unique_active_booking_per_session",
            )
        ]

    def __str__(self):
        return f"{self.user} → {self.session}"

    @property
    def is_paid(self):
        return self.status == self.STATUS_CONFIRMED


class PaymentSettings(models.Model):
    """Singleton: the bank account / QR code shown to users on the payment page."""

    bank_name = models.CharField(max_length=150, default="")
    account_holder = models.CharField(max_length=150, default="")
    account_number = models.CharField(max_length=50, default="")
    qr_image = models.ImageField(upload_to="payment_qr/", blank=True, null=True)
    instructions = models.TextField(
        blank=True,
        default="Scan the QR code with your banking app, transfer the exact amount, then click \"I've made the payment\" below.",
    )

    class Meta:
        verbose_name = "Payment settings"
        verbose_name_plural = "Payment settings"

    def __str__(self):
        return "Payment settings"

    @classmethod
    def get_solo(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj

    @classmethod
    async def aget_solo(cls):
        obj, _ = await cls.objects.aget_or_create(pk=1)
        return obj


class CertificateSettings(models.Model):
    """Singleton: shared template for every certificate PDF."""

    title = models.CharField(max_length=100, default="CERTIFICATE OF COMPLETION")
    intro_text = models.CharField(max_length=200, default="This certificate is proudly presented to")
    completion_text = models.CharField(max_length=200, default="for successfully completing the course")
    signatory_name = models.CharField(max_length=150, default="", blank=True,
                                      help_text="Leave blank to use the session trainer's name.")
    signatory_title = models.CharField(max_length=150, default="", blank=True)
    footer_note = models.CharField(max_length=200, default="", blank=True)
    accent_color = models.CharField(max_length=7, default="#1f3a5f", help_text="Hex colour, e.g. #1f3a5f")
    border_color = models.CharField(max_length=7, default="#c9a227", help_text="Hex colour, e.g. #c9a227")

    class Meta:
        verbose_name = "Certificate settings"
        verbose_name_plural = "Certificate settings"

    def __str__(self):
        return "Certificate settings"

    @classmethod
    def get_solo(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj
