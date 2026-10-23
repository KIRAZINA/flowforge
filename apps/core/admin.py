from django.contrib import admin

from .models import ApiKey


@admin.register(ApiKey)
class ApiKeyAdmin(admin.ModelAdmin):
    list_display = ("name", "user", "prefix", "is_active", "last_used_at", "created_at", "expires_at")
    list_filter = ("is_active", "created_at")
    search_fields = ("name", "prefix", "user__username")
    readonly_fields = ("key", "prefix", "created_at", "last_used_at")
    ordering = ("-created_at",)
