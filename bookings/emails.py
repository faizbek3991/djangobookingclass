from django.conf import settings
from django.core.mail import send_mail


def send_booking_approved_email(booking):
    session = booking.session
    subject = f"Booking confirmed: {session.course.title}"
    message = (
        f"Hi {booking.user.first_name or booking.user.username},\n\n"
        f"Your payment for \"{session.course.title}\" has been verified and your seat is confirmed.\n\n"
        f"Session date & time: {session.start_at:%A, %d %B %Y, %H:%M} - {session.end_at:%H:%M}\n"
        f"Trainer: {session.trainer_name}\n"
        f"Location: {session.location}\n\n"
        f"Join the session using this link:\n{session.meeting_link or '(link will be shared closer to the session)'}\n\n"
        f"Please save this email as your reminder for the session.\n\n"
        f"See you there!\nTrainBook"
    )
    send_mail(
        subject,
        message,
        settings.DEFAULT_FROM_EMAIL,
        [booking.user.email],
        fail_silently=False,
    )
