from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import Company, User


@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    list_display = ["name", "is_active", "phone", "email", "created_at"]
    list_filter = ["is_active"]
    search_fields = ["name", "email", "phone"]


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = ["username", "get_full_name", "person", "company", "role", "is_active"]
    list_filter = ["role", "company", "is_active"]
    fieldsets = UserAdmin.fieldsets + (
        ("GRC", {"fields": ("person", "company", "role")}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        ("GRC", {"fields": ("person", "company", "role")}),
    )
