from django.urls import path

from .views.webhooks import webhook_view
from .views.workflows import EdgeViewSet, NodeViewSet, WorkflowVersionViewSet, WorkflowViewSet

urlpatterns = [
    path(
        "workflows/",
        WorkflowViewSet.as_view({"get": "list", "post": "create"}),
        name="workflow-list",
    ),
    path(
        "workflows/<slug:slug>/",
        WorkflowViewSet.as_view(
            {"get": "retrieve", "patch": "partial_update", "delete": "destroy"}
        ),
        name="workflow-detail",
    ),
    path(
        "workflows/<slug:slug>/versions/",
        WorkflowVersionViewSet.as_view({"get": "list", "post": "create"}),
        name="workflow-version-list",
    ),
    path(
        "workflows/<slug:slug>/versions/<uuid:pk>/",
        WorkflowVersionViewSet.as_view(
            {"get": "retrieve", "patch": "partial_update", "delete": "destroy"}
        ),
        name="workflow-version-detail",
    ),
    path(
        "workflows/<slug:slug>/versions/<uuid:pk>/publish/",
        WorkflowVersionViewSet.as_view({"post": "publish"}),
        name="workflow-version-publish",
    ),
    path(
        "workflows/<slug:slug>/versions/<uuid:version_pk>/nodes/",
        NodeViewSet.as_view({"get": "list", "post": "create"}),
        name="node-list",
    ),
    path(
        "workflows/<slug:slug>/versions/<uuid:version_pk>/nodes/<uuid:pk>/",
        NodeViewSet.as_view({"get": "retrieve", "patch": "partial_update", "delete": "destroy"}),
        name="node-detail",
    ),
    path(
        "workflows/<slug:slug>/versions/<uuid:version_pk>/edges/",
        EdgeViewSet.as_view({"get": "list", "post": "create"}),
        name="edge-list",
    ),
    path(
        "workflows/<slug:slug>/versions/<uuid:version_pk>/edges/<uuid:pk>/",
        EdgeViewSet.as_view({"get": "retrieve", "patch": "partial_update", "delete": "destroy"}),
        name="edge-detail",
    ),
    path("hooks/<slug:workflow_slug>/", webhook_view, name="webhook"),
    path("hooks/<slug:workflow_slug>/<path:trigger_path>/", webhook_view, name="webhook-path"),
]
