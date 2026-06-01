from django.contrib import admin
from .models import Participation


@admin.register(Participation)
class ParticipationAdmin(admin.ModelAdmin):
    list_display = ["company_person", "session", "role", "chosen_position", "company"]
    list_filter = ["company", "role", "session__course"]
    search_fields = [
        "company_person__person__last_name",
        "company_person__person__first_name",
        "session__label",
        "session__course__name",
    ]
    raw_id_fields = ["company_person", "session"]
