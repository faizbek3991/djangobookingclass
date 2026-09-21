from datetime import datetime
from decimal import Decimal
from typing import Optional

from ninja import Schema


class BookingOut(Schema):
    id: int
    status: str
    amount_due: Decimal
    booked_at: datetime
    submitted_at: Optional[datetime] = None
    paid_at: Optional[datetime] = None

    session_id: int
    course_title: str
    session_start_at: datetime
    session_end_at: datetime
    meeting_link: Optional[str] = None

    @staticmethod
    def resolve_course_title(obj):
        return obj.session.course.title

    @staticmethod
    def resolve_session_start_at(obj):
        return obj.session.start_at

    @staticmethod
    def resolve_session_end_at(obj):
        return obj.session.end_at

    @staticmethod
    def resolve_meeting_link(obj):
        # Only reveal the meeting link once the payment is actually confirmed.
        if obj.status == "confirmed":
            return obj.session.meeting_link or None
        return None


class BookingCreateIn(Schema):
    session_id: int


class BookingRescheduleIn(Schema):
    session_id: int


class PaymentSettingsOut(Schema):
    bank_name: str
    account_holder: str
    account_number: str
    instructions: str
    qr_image_url: Optional[str] = None

    @staticmethod
    def resolve_qr_image_url(obj):
        return obj.qr_image.url if obj.qr_image else None


class PaymentSettingsIn(Schema):
    bank_name: str
    account_holder: str
    account_number: str
    instructions: str = ""


class MessageOut(Schema):
    detail: str
