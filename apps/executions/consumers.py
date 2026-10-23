import json

from asgiref.sync import sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer

from apps.executions.models import Execution, ExecutionLog


def _serialize_log(log: ExecutionLog) -> dict:
    return {
        "id": str(log.id),
        "execution_id": str(log.execution_id),
        "level": log.level,
        "message": log.message,
        "data": log.data,
        "node_id": str(log.node_id) if log.node_id else None,
        "created_at": log.created_at.isoformat() if log.created_at else None,
    }


class ExecutionLogConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.execution_id = self.scope["url_route"]["kwargs"]["execution_id"]
        exists = await sync_to_async(
            lambda: Execution.objects.filter(pk=self.execution_id).exists()
        )()
        if not exists:
            await self.close(code=4404)
            return

        self.group_name = f"execution_{self.execution_id}"
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

        history = await sync_to_async(list)(
            ExecutionLog.objects.filter(execution_id=self.execution_id).order_by("created_at")
        )
        for log in history:
            await self.send(text_data=json.dumps(_serialize_log(log)))

    async def disconnect(self, close_code):
        if hasattr(self, "group_name"):
            await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def execution_log(self, event):
        await self.send(text_data=json.dumps(event["payload"]))
