from datetime import datetime
from decimal import Decimal
from typing import Optional

from ninja import Schema


class SessionOut(Schema):
    """Public-facing session info — no meeting_link (only revealed to the booking owner once confirmed)."""

    id: int
    trainer_name: str
    start_at: datetime
    end_at: datetime
    location: str
    capacity: int
    seats_taken: int
    seats_left: int
    is_full: bool
    is_past: bool


class CourseOut(Schema):
    id: int
    title: str
    slug: str
    description: str
    price: Decimal
    duration_hours: int
    is_active: bool
    upcoming_sessions_count: int

    @staticmethod
    def resolve_upcoming_sessions_count(obj):
        return obj.upcoming_sessions.count()


class CourseDetailOut(CourseOut):
    sessions: list[SessionOut] = []

    @staticmethod
    def resolve_sessions(obj):
        return list(obj.upcoming_sessions)


class CourseAdminOut(CourseOut):
    meta_title: str
    meta_description: str
    og_image_url: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    @staticmethod
    def resolve_og_image_url(obj):
        return obj.og_image.url if obj.og_image else None


class CourseIn(Schema):
    title: str
    description: str
    price: Decimal
    duration_hours: int
    is_active: bool = True
    meta_title: str = ""
    meta_description: str = ""


class SessionAdminOut(SessionOut):
    course_id: int
    course_title: str
    meeting_link: str

    @staticmethod
    def resolve_course_title(obj):
        return obj.course.title


class SessionIn(Schema):
    course_id: int
    trainer_name: str
    start_at: datetime
    end_at: datetime
    location: str = "Online (link sent after booking)"
    capacity: int = 20
    meeting_link: str = ""


class SEOSettingsOut(Schema):
    site_name: str
    default_meta_title: str
    default_meta_description: str
    default_og_image_url: Optional[str] = None
    google_site_verification: str

    @staticmethod
    def resolve_default_og_image_url(obj):
        return obj.default_og_image.url if obj.default_og_image else None


class SEOSettingsIn(Schema):
    site_name: str
    default_meta_title: str
    default_meta_description: str
    google_site_verification: str = ""


class MessageOut(Schema):
    detail: str
