from django.contrib import admin

from .models import Edge, Node, Trigger, Workflow, WorkflowVersion


@admin.register(Workflow)
class WorkflowAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "is_active", "is_public", "created_by", "created_at")
    list_filter = ("is_active", "is_public", "created_at")
    search_fields = ("name", "slug", "description")
    readonly_fields = ("id", "created_at", "updated_at")
    prepopulated_fields = {"slug": ("name",)}


@admin.register(WorkflowVersion)
class WorkflowVersionAdmin(admin.ModelAdmin):
    list_display = ("workflow", "version_number", "is_published", "created_at")
    list_filter = ("is_published", "created_at")
    search_fields = ("workflow__name",)
    readonly_fields = ("id", "created_at")


@admin.register(Node)
class NodeAdmin(admin.ModelAdmin):
    list_display = ("name", "key", "node_type", "workflow_version", "created_at")
    list_filter = ("node_type", "created_at")
    search_fields = ("name", "key", "workflow_version__workflow__name")
    readonly_fields = ("id", "created_at")


@admin.register(Edge)
class EdgeAdmin(admin.ModelAdmin):
    list_display = ("source_node", "target_node", "source_handle", "target_handle", "created_at")
    list_filter = ("created_at",)
    search_fields = ("source_node__key", "target_node__key")
    readonly_fields = ("id", "created_at")


@admin.register(Trigger)
class TriggerAdmin(admin.ModelAdmin):
    list_display = ("workflow", "trigger_type", "is_active", "created_at")
    list_filter = ("trigger_type", "is_active", "created_at")
    search_fields = ("workflow__name",)
    readonly_fields = ("id", "created_at")
