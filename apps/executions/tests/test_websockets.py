import os
os.environ.setdefault("DJANGO_ALLOW_ASYNC_UNSAFE", "1")

import json
import pytest
from channels.testing import WebsocketCommunicator
from django.contrib.auth import get_user_model
from django.test import override_settings

from asgiref.sync import sync_to_async
from channels.routing import URLRouter

from apps.executions.routing import websocket_urlpatterns
from apps.executions.models import Execution, ExecutionLog
from apps.executions.realtime import broadcast_execution_log
from apps.workflows.models import Workflow, WorkflowVersion

User = get_user_model()

TEST_CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels.layers.InMemoryChannelLayer",
    }
}


@pytest.mark.django_db
@override_settings(CHANNEL_LAYERS=TEST_CHANNEL_LAYERS)
@pytest.mark.asyncio
async def test_consumer_receives_broadcast():
    user = User.objects.create_user("wsuser", "ws@example.com", "pass")
    workflow = Workflow.objects.create(name="WS", slug="ws", created_by=user)
    version = WorkflowVersion.objects.create(workflow=workflow, version_number=1, is_published=True)
    execution = Execution.objects.create(workflow_version=version, input_payload={})

    communicator = WebsocketCommunicator(
        URLRouter(websocket_urlpatterns), f"/ws/executions/{execution.id}/logs/"
    )
    connected, _ = await communicator.connect()
    assert connected is True

    log = ExecutionLog.objects.create(
        execution=execution, level="info", message="hello", data={"x": 1}
    )
    await sync_to_async(broadcast_execution_log)(log)

    response = await communicator.receive_json_from()
    assert response["message"] == "hello"
    assert response["level"] == "info"

    await communicator.disconnect()


@pytest.mark.django_db
@override_settings(CHANNEL_LAYERS=TEST_CHANNEL_LAYERS)
@pytest.mark.asyncio
async def test_consumer_sends_history():
    user = User.objects.create_user("wsuser2", "ws2@example.com", "pass")
    workflow = Workflow.objects.create(name="WS2", slug="ws2", created_by=user)
    version = WorkflowVersion.objects.create(workflow=workflow, version_number=1, is_published=True)
    execution = Execution.objects.create(workflow_version=version, input_payload={})
    ExecutionLog.objects.create(execution=execution, level="info", message="old", data={})

    communicator = WebsocketCommunicator(
        URLRouter(websocket_urlpatterns), f"/ws/executions/{execution.id}/logs/"
    )
    connected, _ = await communicator.connect()
    assert connected is True
    response = await communicator.receive_json_from()
    assert response["message"] == "old"
    await communicator.disconnect()


@pytest.mark.django_db
@override_settings(CHANNEL_LAYERS=TEST_CHANNEL_LAYERS)
@pytest.mark.asyncio
async def test_consumer_rejects_unknown_execution():
    communicator = WebsocketCommunicator(
        URLRouter(websocket_urlpatterns), "/ws/executions/00000000-0000-0000-0000-000000000000/logs/"
    )
    connected, close_code = await communicator.connect()
    assert connected is False
