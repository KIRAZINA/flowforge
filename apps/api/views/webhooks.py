from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from apps.workflows.models import Trigger, Workflow


def _latest_published_version(workflow):
    return workflow.versions.filter(is_published=True).order_by("-version_number").first()


def _select_trigger(workflow, trigger_path):
    triggers = list(
        Trigger.objects.filter(workflow=workflow, trigger_type="webhook", is_active=True)
    )
    wanted = trigger_path or ""
    for trigger in triggers:
        if (trigger.config or {}).get("path", "") == wanted:
            return trigger
    if triggers and not trigger_path:
        # Fall back to the first active webhook trigger without a specific path.
        for trigger in triggers:
            if not (trigger.config or {}).get("path"):
                return trigger
    # Create a default trigger on first use so webhooks are self-service.
    config = {"path": trigger_path} if trigger_path else {}
    return Trigger.objects.create(
        workflow=workflow, trigger_type="webhook", is_active=True, config=config
    )


@api_view(["GET", "POST", "PUT", "PATCH", "DELETE"])
@permission_classes([AllowAny])
def webhook_view(request, workflow_slug, trigger_path=None):
    workflow = Workflow.objects.filter(slug=workflow_slug, is_active=True).first()
    if workflow is None:
        return Response({"detail": "Workflow not found."}, status=status.HTTP_404_NOT_FOUND)

    version = _latest_published_version(workflow)
    if version is None:
        return Response(
            {"detail": "No published workflow version available."},
            status=status.HTTP_409_CONFLICT,
        )

    trigger = _select_trigger(workflow, trigger_path)

    allowed_methods = (trigger.config or {}).get("methods") or (trigger.config or {}).get("method") or ["POST"]
    if isinstance(allowed_methods, str):
        allowed_methods = [allowed_methods]
    allowed_methods = [str(method).upper() for method in allowed_methods]
    if request.method.upper() not in allowed_methods:
        return Response({"detail": "Method not allowed."}, status=status.HTTP_405_METHOD_NOT_ALLOWED)

    secret = (trigger.config or {}).get("secret")
    if secret:
        provided = request.headers.get("X-FlowForge-Secret") or request.query_params.get("secret")
        if provided != secret:
            return Response({"detail": "Invalid secret."}, status=status.HTTP_403_FORBIDDEN)

    if isinstance(request.data, dict):
        payload = request.data
    elif request.data in (None, ""):
        payload = {}
    else:
        payload = {"data": request.data}

    from apps.executions.services import start_execution

    execution = start_execution(
        version.id, input_payload=payload, trigger_type="webhook"
    )
    return Response(
        {"execution_id": str(execution.id), "status": "pending"},
        status=status.HTTP_202_ACCEPTED,
    )
