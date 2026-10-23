from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

from .models import ExecutionLog


def serialize_execution_log(log: ExecutionLog) -> dict:
    return {
        "id": str(log.id),
        "execution_id": str(log.execution_id),
        "level": log.level,
        "message": log.message,
        "data": log.data,
        "node_id": str(log.node_id) if log.node_id else None,
        "created_at": log.created_at.isoformat() if log.created_at else None,
    }


def broadcast_execution_log(log: ExecutionLog) -> None:
    channel_layer = get_channel_layer()
    if channel_layer is None:
        return
    try:
        async_to_sync(channel_layer.group_send)(
            f"execution_{log.execution_id}",
            {"type": "execution.log", "payload": serialize_execution_log(log)},
        )
    except Exception:
        # Real-time delivery is best-effort and must not break execution.
        return
