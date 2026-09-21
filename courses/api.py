from django.shortcuts import get_object_or_404
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


# ---- Public ----

@public_router.get("/", response=list[CourseOut])
def list_courses(request):
    return list(Course.objects.filter(is_active=True))


@public_router.get("/{slug}/", response=CourseDetailOut)
def get_course(request, slug: str):
    return get_object_or_404(Course, slug=slug, is_active=True)


# ---- Admin: Course CRUD ----

@admin_courses_router.get("/", response=list[CourseAdminOut])
def admin_list_courses(request):
    return list(Course.objects.all())


@admin_courses_router.get("/{course_id}/", response=CourseAdminOut)
def admin_get_course(request, course_id: int):
    return get_object_or_404(Course, pk=course_id)


@admin_courses_router.post("/", response={201: CourseAdminOut})
def admin_create_course(request, payload: CourseIn):
    course = Course.objects.create(**payload.dict())
    return 201, course


@admin_courses_router.put("/{course_id}/", response=CourseAdminOut)
def admin_update_course(request, course_id: int, payload: CourseIn):
    course = get_object_or_404(Course, pk=course_id)
    for field, value in payload.dict().items():
        setattr(course, field, value)
    course.save()
    return course


@admin_courses_router.delete("/{course_id}/", response=MessageOut)
def admin_delete_course(request, course_id: int):
    course = get_object_or_404(Course, pk=course_id)
    course.delete()
    return {"detail": "Course deleted."}


@admin_courses_router.post("/{course_id}/image/", response=CourseAdminOut)
def admin_set_course_image(request, course_id: int, image: UploadedFile = File(...)):
    course = get_object_or_404(Course, pk=course_id)
    course.og_image = image
    course.save()
    return course


# ---- Admin: Session CRUD ----

@admin_sessions_router.get("/", response=list[SessionAdminOut])
def admin_list_sessions(request):
    return list(Session.objects.select_related("course").all())


@admin_sessions_router.get("/{session_id}/", response=SessionAdminOut)
def admin_get_session(request, session_id: int):
    return get_object_or_404(Session, pk=session_id)


@admin_sessions_router.post("/", response={201: SessionAdminOut, 400: MessageOut})
def admin_create_session(request, payload: SessionIn):
    if payload.end_at <= payload.start_at:
        return 400, {"detail": "End time must be after the start time."}
    course = get_object_or_404(Course, pk=payload.course_id)
    session = Session.objects.create(
        course=course,
        trainer_name=payload.trainer_name,
        start_at=payload.start_at,
        end_at=payload.end_at,
        location=payload.location,
        capacity=payload.capacity,
        meeting_link=payload.meeting_link,
    )
    return 201, session


@admin_sessions_router.put("/{session_id}/", response={200: SessionAdminOut, 400: MessageOut})
def admin_update_session(request, session_id: int, payload: SessionIn):
    if payload.end_at <= payload.start_at:
        return 400, {"detail": "End time must be after the start time."}
    session = get_object_or_404(Session, pk=session_id)
    session.course = get_object_or_404(Course, pk=payload.course_id)
    session.trainer_name = payload.trainer_name
    session.start_at = payload.start_at
    session.end_at = payload.end_at
    session.location = payload.location
    session.capacity = payload.capacity
    session.meeting_link = payload.meeting_link
    session.save()
    return session


@admin_sessions_router.delete("/{session_id}/", response=MessageOut)
def admin_delete_session(request, session_id: int):
    session = get_object_or_404(Session, pk=session_id)
    session.delete()
    return {"detail": "Session deleted."}


# ---- Admin: SEO settings ----

@admin_seo_router.get("/", response=SEOSettingsOut)
def admin_get_seo_settings(request):
    return SiteSEOSettings.get_solo()


@admin_seo_router.put("/", response=SEOSettingsOut)
def admin_update_seo_settings(request, payload: SEOSettingsIn):
    settings_obj = SiteSEOSettings.get_solo()
    for field, value in payload.dict().items():
        setattr(settings_obj, field, value)
    settings_obj.save()
    return settings_obj


@admin_seo_router.post("/image/", response=SEOSettingsOut)
def admin_set_seo_image(request, image: UploadedFile = File(...)):
    settings_obj = SiteSEOSettings.get_solo()
    settings_obj.default_og_image = image
    settings_obj.save()
    return settings_obj
