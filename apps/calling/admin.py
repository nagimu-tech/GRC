from django.contrib import admin
from .models import Event, CallRecord


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = ["title", "company", "course", "date", "is_active"]
    list_filter = ["company", "is_active", "course"]
    search_fields = ["title"]
    filter_horizontal = ["assigned_callers"]


@admin.register(CallRecord)
class CallRecordAdmin(admin.ModelAdmin):
    list_display = ["company_person", "event", "status", "called_by", "claimed_by", "updated_at"]
    list_filter = ["event__company", "status", "event"]
    search_fields = ["company_person__person__last_name", "event__title"]
    raw_id_fields = ["company_person", "called_by", "claimed_by"]
