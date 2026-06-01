from django.contrib import admin
from .models import Position, Course, CourseSession, CourseSessionPhoto


@admin.register(Position)
class PositionAdmin(admin.ModelAdmin):
    list_display = ["name", "is_active", "order"]
    list_filter = ["is_active"]
    search_fields = ["name"]
    ordering = ["order", "name"]


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ["name", "company", "is_active"]
    list_filter = ["company", "is_active"]
    search_fields = ["name"]


@admin.register(CourseSession)
class CourseSessionAdmin(admin.ModelAdmin):
    list_display = ["label", "course", "company", "start_date", "end_date", "location_format"]
    list_filter = ["company", "location_format"]
    search_fields = ["label", "course__name"]


@admin.register(CourseSessionPhoto)
class CourseSessionPhotoAdmin(admin.ModelAdmin):
    list_display = ["session", "caption", "order", "created_at"]
    search_fields = ["session__label", "session__course__name", "caption"]
    raw_id_fields = ["session"]
