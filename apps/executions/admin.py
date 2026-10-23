from django.contrib import admin

from .models import Execution, ExecutionLog


@admin.register(Execution)
class ExecutionAdmin(admin.ModelAdmin):
    list_display = ("id", "workflow_version", "status", "trigger_type", "created_by", "created_at")
    list_filter = ("status", "trigger_type", "created_at")
    search_fields = ("id", "workflow_version__workflow__name", "error_message")
    readonly_fields = ("id", "created_at", "started_at", "finished_at")


@admin.register(ExecutionLog)
class ExecutionLogAdmin(admin.ModelAdmin):
    list_display = ("execution", "node", "level", "message", "created_at")
    list_filter = ("level", "created_at")
    search_fields = ("message", "execution__id")
    readonly_fields = ("id", "created_at")
