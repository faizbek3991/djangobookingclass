from datetime import date, timedelta

from django.contrib.auth.models import User
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from courses.models import Course, Session

from .certificates import build_certificate_pdf, certificate_eligible, certificate_fields
from .models import Booking


# Tests render pages that use {% static %}; skip the manifest storage that needs collectstatic.
@override_settings(STORAGES={
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
})
class CertificateTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("peserta", password="x", first_name="Ahmad", last_name="Faiz")
        self.staff = User.objects.create_user("admin", password="x", is_staff=True)
        course = Course.objects.create(title="Full Stack Python", slug="fsp", price=250, duration_hours=15)
        now = timezone.now()
        self.ended = Session.objects.create(course=course, start_at=now - timedelta(days=3, hours=3),
                                            end_at=now - timedelta(days=3), trainer_name="Cikgu Faiz", capacity=10)
        self.upcoming = Session.objects.create(course=course, start_at=now + timedelta(days=3),
                                               end_at=now + timedelta(days=3, hours=3), trainer_name="Cikgu Faiz",
                                               capacity=10)

    def booking(self, session, status=Booking.STATUS_CONFIRMED, user=None, **kw):
        return Booking.objects.create(user=user or self.user, session=session, status=status, amount_due=250, **kw)

    def test_eligible_only_when_confirmed_and_session_ended(self):
        other = User.objects.create_user("lain2", password="x")
        self.assertTrue(certificate_eligible(self.booking(self.ended)))
        self.assertFalse(certificate_eligible(self.booking(self.upcoming, user=other)))
        pending = User.objects.create_user("lain3", password="x")
        self.assertFalse(certificate_eligible(self.booking(self.ended, status=Booking.STATUS_PENDING_PAYMENT, user=pending)))

    def test_fields_fall_back_to_user_and_session_data(self):
        f = certificate_fields(self.booking(self.ended))
        self.assertEqual(f["name"], "Ahmad Faiz")
        self.assertEqual(f["course"], "Full Stack Python")
        self.assertEqual(f["date"], self.ended.start_at.date())

    def test_overrides_take_precedence(self):
        b = self.booking(self.ended, cert_name="Ahmad bin Abdullah", cert_course_title="FSP Batch 1",
                         cert_date=date(2026, 11, 1))
        f = certificate_fields(b)
        self.assertEqual(f["name"], "Ahmad bin Abdullah")
        self.assertEqual(f["course"], "FSP Batch 1")
        self.assertEqual(f["date"], date(2026, 11, 1))

    def test_pdf_is_generated(self):
        self.assertTrue(build_certificate_pdf(self.booking(self.ended)).read(5).startswith(b"%PDF"))

    def test_owner_can_download_only_eligible_certificate(self):
        ok = self.booking(self.ended)
        not_yet = self.booking(self.upcoming)  # same user, different session
        self.client.force_login(self.user)
        r = self.client.get(reverse("bookings:certificate_download", args=[ok.pk]))
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r["Content-Type"], "application/pdf")
        self.assertEqual(self.client.get(reverse("bookings:certificate_download", args=[not_yet.pk])).status_code, 404)

    def test_user_cannot_download_someone_elses_certificate(self):
        other = User.objects.create_user("lain", password="x")
        b = self.booking(self.ended)  # owned by self.user
        self.client.force_login(other)
        self.assertEqual(self.client.get(reverse("bookings:certificate_download", args=[b.pk])).status_code, 404)

    def test_admin_certificate_pages_require_staff(self):
        self.booking(self.ended)
        self.client.force_login(self.user)
        self.assertNotEqual(self.client.get(reverse("bookings:admin_certificate_list")).status_code, 200)
        self.client.force_login(self.staff)
        self.assertEqual(self.client.get(reverse("bookings:admin_certificate_list")).status_code, 200)
