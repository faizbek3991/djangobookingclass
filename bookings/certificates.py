"""Certificate generation. A certificate exists for a confirmed booking once its session has ended.
Generated on demand from current data, so there is nothing to store or regenerate."""
import io

from django.utils import timezone
from reportlab.lib.colors import HexColor
from reportlab.lib.pagesizes import A4, landscape
from reportlab.pdfgen import canvas

from .models import CertificateSettings


def certificate_eligible(booking):
    return booking.status == booking.STATUS_CONFIRMED and booking.session.end_at <= timezone.now()


def certificate_id(booking):
    return f"TB-{booking.session.start_at:%Y%m%d}-{booking.pk:05d}"


def _safe_color(value, default):
    try:
        return HexColor(value)
    except Exception:
        return HexColor(default)


def certificate_fields(booking):
    """Resolve what the certificate shows: per-booking override first, then the session/user data."""
    return {
        "name": booking.cert_name or booking.user.get_full_name() or booking.user.username,
        "course": booking.cert_course_title or booking.session.course.title,
        "date": booking.cert_date or booking.session.start_at.date(),
        "trainer": booking.session.trainer_name,
    }


def build_certificate_pdf(booking):
    cfg = CertificateSettings.get_solo()
    fields = certificate_fields(booking)
    accent = _safe_color(cfg.accent_color, "#1f3a5f")
    border = _safe_color(cfg.border_color, "#c9a227")
    buf = io.BytesIO()
    w, h = landscape(A4)
    c = canvas.Canvas(buf, pagesize=(w, h))
    c.setTitle(f"Certificate - {fields['name']}")

    c.setFillColor(accent)
    c.rect(0, 0, w, h, fill=1, stroke=0)
    c.setFillColor(HexColor("#fdfbf4"))
    c.rect(20, 20, w - 40, h - 40, fill=1, stroke=0)
    c.setStrokeColor(border)
    c.setLineWidth(3)
    c.rect(34, 34, w - 68, h - 68, fill=0, stroke=1)

    # Vertical layout is measured from the top; the block is centred within the frame.
    top = h - 150
    grey = HexColor("#444444")

    def line(dy, text, font="Helvetica", size=16, color=None):
        c.setFillColor(color or accent)
        c.setFont(font, size)
        c.drawCentredString(w / 2, top - dy, text)

    line(0, cfg.title, "Helvetica-Bold", 34)
    line(44, cfg.intro_text, size=16, color=grey)
    line(90, fields["name"], "Helvetica-Bold", 30)
    line(130, cfg.completion_text, size=16, color=grey)
    line(165, fields["course"], "Helvetica-Bold", 22)
    line(205, f"Session date: {fields['date']:%d %B %Y}   |   Duration: {booking.session.course.duration_hours} hours",
         size=14, color=grey)
    line(228, f"Trainer: {fields['trainer']}", size=14, color=grey)

    signer = cfg.signatory_name or fields["trainer"]
    c.setStrokeColor(border)
    c.setLineWidth(1)
    c.line(w / 2 - 120, 150, w / 2 + 120, 150)
    c.setFillColor(grey)
    c.setFont("Helvetica", 11)
    c.drawCentredString(w / 2, 134, signer)
    if cfg.signatory_title:
        c.drawCentredString(w / 2, 120, cfg.signatory_title)

    c.drawString(90, 80, f"Certificate No: {certificate_id(booking)}")
    c.drawRightString(w - 90, 80, f"Issued: {timezone.localdate():%d %B %Y}")
    if cfg.footer_note:
        c.drawCentredString(w / 2, 60, cfg.footer_note)

    c.showPage()
    c.save()
    buf.seek(0)
    return buf
