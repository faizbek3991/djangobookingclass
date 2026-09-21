from django.db.models import Count, Q
from django.shortcuts import aget_object_or_404
from django.utils import timezone
from ninja import File, Router
from ninja.files import UploadedFile
from ninja.security import django_auth_is_staff

from .models import Course, Session, SiteSEOSettings
from .schemas import (
    CourseAdminOut,
    CourseDetailOut,
    CourseIn,
    CourseOut,
    MessageOut,
    SEOSettingsIn,
    SEOSettingsOut,
    SessionAdminOut,
    SessionIn,
    SessionOut,
)

public_router = Router(tags=["courses"], auth=None)
admin_courses_router = Router(tags=["admin: courses"], auth=django_auth_is_staff)
admin_sessions_router = Router(tags=["admin: sessions"], auth=django_auth_is_staff)
admin_seo_router = Router(tags=["admin: seo"], auth=django_auth_is_staff)

ACTIVE_BOOKING_STATUSES = ["pending_payment", "awaiting_verification", "confirmed"]


def _with_booked_count(session_queryset):
    """Annotates each session with `_booked_count` — see schemas.py's SessionOut docstring."""
    return session_queryset.annotate(
        _booked_count=Count("bookings", filter=Q(bookings__status__in=ACTIVE_BOOKING_STATUSES))
    )


def _with_upcoming_count(course_queryset):
    """Annotates each course with `_upcoming_count` — see schemas.py's CourseOut docstring."""
    return course_queryset.annotate(
        _upcoming_count=Count("sessions", filter=Q(sessions__start_at__gte=timezone.now()))
    )


# ---- Public ----

@public_router.get("/", response=list[CourseOut])
async def list_courses(request):
    qs = _with_upcoming_count(Course.objects.filter(is_active=True))
    return [c async for c in qs]


@public_router.get("/{slug}/", response=CourseDetailOut)
async def get_course(request, slug: str):
    course = await aget_object_or_404(Course, slug=slug, is_active=True)
    sessions_qs = _with_booked_count(course.sessions.filter(start_at__gte=timezone.now())).order_by("start_at")
    course._prefetched_sessions = [s async for s in sessions_qs]
    course._upcoming_count = len(course._prefetched_sessions)
    return course


# ---- Admin: Course CRUD ----

@admin_courses_router.get("/", response=list[CourseAdminOut])
async def admin_list_courses(request):
    qs = _with_upcoming_count(Course.objects.all())
    return [c async for c in qs]


@admin_courses_router.get("/{course_id}/", response=CourseAdminOut)
async def admin_get_course(request, course_id: int):
    course = await aget_object_or_404(Course, pk=course_id)
    course._upcoming_count = await course.sessions.filter(start_at__gte=timezone.now()).acount()
    return course


@admin_courses_router.post("/", response={201: CourseAdminOut})
async def admin_create_course(request, payload: CourseIn):
    course = await Course.objects.acreate(**payload.dict())
    course._upcoming_count = 0
    return 201, course


@admin_courses_router.put("/{course_id}/", response=CourseAdminOut)
async def admin_update_course(request, course_id: int, payload: CourseIn):
    course = await aget_object_or_404(Course, pk=course_id)
    for field, value in payload.dict().items():
        setattr(course, field, value)
    await course.asave()
    course._upcoming_count = await course.sessions.filter(start_at__gte=timezone.now()).acount()
    return course


@admin_courses_router.delete("/{course_id}/", response=MessageOut)
async def admin_delete_course(request, course_id: int):
    course = await aget_object_or_404(Course, pk=course_id)
    await course.adelete()
    return {"detail": "Course deleted."}


@admin_courses_router.post("/{course_id}/image/", response=CourseAdminOut)
async def admin_set_course_image(request, course_id: int, image: UploadedFile = File(...)):
    course = await aget_object_or_404(Course, pk=course_id)
    course.og_image = image
    await course.asave()
    course._upcoming_count = await course.sessions.filter(start_at__gte=timezone.now()).acount()
    return course


# ---- Admin: Session CRUD ----

@admin_sessions_router.get("/", response=list[SessionAdminOut])
async def admin_list_sessions(request):
    qs = _with_booked_count(Session.objects.select_related("course").all())
    return [s async for s in qs]


@admin_sessions_router.get("/{session_id}/", response=SessionAdminOut)
async def admin_get_session(request, session_id: int):
    session = await aget_object_or_404(Session.objects.select_related("course"), pk=session_id)
    session._booked_count = await session.bookings.filter(status__in=ACTIVE_BOOKING_STATUSES).acount()
    return session


@admin_sessions_router.post("/", response={201: SessionAdminOut, 400: MessageOut})
async def admin_create_session(request, payload: SessionIn):
    if payload.end_at <= payload.start_at:
        return 400, {"detail": "End time must be after the start time."}
    course = await aget_object_or_404(Course, pk=payload.course_id)
    session = await Session.objects.acreate(
        course=course,
        trainer_name=payload.trainer_name,
        start_at=payload.start_at,
        end_at=payload.end_at,
        location=payload.location,
        capacity=payload.capacity,
        meeting_link=payload.meeting_link,
    )
    session._booked_count = 0
    return 201, session


@admin_sessions_router.put("/{session_id}/", response={200: SessionAdminOut, 400: MessageOut})
async def admin_update_session(request, session_id: int, payload: SessionIn):
    if payload.end_at <= payload.start_at:
        return 400, {"detail": "End time must be after the start time."}
    session = await aget_object_or_404(Session.objects.select_related("course"), pk=session_id)
    session.course = await aget_object_or_404(Course, pk=payload.course_id)
    session.trainer_name = payload.trainer_name
    session.start_at = payload.start_at
    session.end_at = payload.end_at
    session.location = payload.location
    session.capacity = payload.capacity
    session.meeting_link = payload.meeting_link
    await session.asave()
    session._booked_count = await session.bookings.filter(status__in=ACTIVE_BOOKING_STATUSES).acount()
    return session


@admin_sessions_router.delete("/{session_id}/", response=MessageOut)
async def admin_delete_session(request, session_id: int):
    session = await aget_object_or_404(Session, pk=session_id)
    await session.adelete()
    return {"detail": "Session deleted."}


# ---- Admin: SEO settings ----

@admin_seo_router.get("/", response=SEOSettingsOut)
async def admin_get_seo_settings(request):
    return await SiteSEOSettings.aget_solo()


@admin_seo_router.put("/", response=SEOSettingsOut)
async def admin_update_seo_settings(request, payload: SEOSettingsIn):
    settings_obj = await SiteSEOSettings.aget_solo()
    for field, value in payload.dict().items():
        setattr(settings_obj, field, value)
    await settings_obj.asave()
    return settings_obj


@admin_seo_router.post("/image/", response=SEOSettingsOut)
async def admin_set_seo_image(request, image: UploadedFile = File(...)):
    settings_obj = await SiteSEOSettings.aget_solo()
    settings_obj.default_og_image = image
    await settings_obj.asave()
    return settings_obj
