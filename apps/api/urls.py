from django.urls import path

from .views.webhooks import webhook_view

urlpatterns = [
    path("hooks/<slug:workflow_slug>/", webhook_view, name="webhook"),
    path("hooks/<slug:workflow_slug>/<path:trigger_path>/", webhook_view, name="webhook-path"),
]
