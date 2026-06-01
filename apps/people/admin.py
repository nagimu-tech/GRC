from django.contrib import admin
from .models import Person, CompanyPerson, CompanyPersonPhoto


@admin.register(Person)
class PersonAdmin(admin.ModelAdmin):
    list_display = ["full_name", "phone", "email", "birth_date", "created_at"]
    search_fields = ["last_name", "first_name", "middle_name", "phone", "email"]
    readonly_fields = ["created_at", "updated_at"]


@admin.register(CompanyPerson)
class CompanyPersonAdmin(admin.ModelAdmin):
    list_display = ["full_name", "company", "is_active", "consent_stored", "consent_contact"]
    list_filter = ["company", "is_active", "consent_stored", "consent_contact"]
    search_fields = ["person__last_name", "person__first_name", "person__phone"]
    raw_id_fields = ["person"]


@admin.register(CompanyPersonPhoto)
class CompanyPersonPhotoAdmin(admin.ModelAdmin):
    list_display = ["company_person", "caption", "order", "created_at"]
    search_fields = ["company_person__person__last_name", "company_person__person__first_name", "caption"]
    raw_id_fields = ["company_person"]
