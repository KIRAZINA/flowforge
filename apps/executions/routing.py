from django.urls import re_path

from . import consumers

websocket_urlpatterns = [
    re_path(
        r"ws/executions/(?P<execution_id>[0-9a-fA-F-]+)/logs/$",
        consumers.ExecutionLogConsumer.as_asgi(),
    ),
]
