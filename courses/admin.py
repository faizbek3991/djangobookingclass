from django.contrib import admin

from .models import Course, Session, SiteSEOSettings


class SessionInline(admin.TabularInline):
    model = Session
    extra = 1


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ("title", "price", "duration_hours", "is_active", "created_at")
    list_filter = ("is_active",)
    search_fields = ("title", "description")
    prepopulated_fields = {"slug": ("title",)}
    inlines = [SessionInline]


@admin.register(Session)
class SessionAdmin(admin.ModelAdmin):
    list_display = ("course", "trainer_name", "start_at", "end_at", "capacity", "seats_taken")
    list_filter = ("course",)
    date_hierarchy = "start_at"


@admin.register(SiteSEOSettings)
class SiteSEOSettingsAdmin(admin.ModelAdmin):
    list_display = ("site_name", "default_meta_title")
