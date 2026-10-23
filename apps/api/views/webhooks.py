import hashlib
import hmac

from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes, throttle_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from apps.api.throttling import WebhookRateThrottle
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


def _authenticate_api_key(request):
    raw_key = None
    auth_header = request.headers.get("Authorization", "")
    if auth_header.lower().startswith("api-key "):
        raw_key = auth_header.split(" ", 1)[1].strip()
    elif request.headers.get("X-API-Key"):
        raw_key = request.headers.get("X-API-Key").strip()

    if not raw_key:
        return None

    from apps.core.models import ApiKey

    prefix = raw_key[:12]
    expected = hashlib.sha256(raw_key.encode("utf-8")).hexdigest()
    for api_key in ApiKey.objects.filter(prefix=prefix, is_active=True).select_related("user"):
        if api_key.expires_at and api_key.expires_at < timezone.now():
            continue
        if hmac.compare_digest(api_key.key, expected):
            api_key.last_used_at = timezone.now()
            api_key.save(update_fields=["last_used_at"])
            return api_key.user
    return "invalid"


@api_view(["GET", "POST", "PUT", "PATCH", "DELETE"])
@permission_classes([AllowAny])
@throttle_classes([WebhookRateThrottle])
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

    allowed_methods = (
        (trigger.config or {}).get("methods") or (trigger.config or {}).get("method") or ["POST"]
    )
    if isinstance(allowed_methods, str):
        allowed_methods = [allowed_methods]
    allowed_methods = [str(method).upper() for method in allowed_methods]
    if request.method.upper() not in allowed_methods:
        return Response(
            {"detail": "Method not allowed."}, status=status.HTTP_405_METHOD_NOT_ALLOWED
        )

    api_key_user = _authenticate_api_key(request)
    if api_key_user == "invalid":
        return Response({"detail": "Invalid API key."}, status=status.HTTP_401_UNAUTHORIZED)

    triggered_by = None
    if api_key_user is not None:
        if workflow.created_by != api_key_user and not getattr(api_key_user, "is_staff", False):
            return Response({"detail": "Forbidden."}, status=status.HTTP_403_FORBIDDEN)
        triggered_by = api_key_user
    else:
        secret = (trigger.config or {}).get("secret")
        if secret:
            provided = request.headers.get("X-FlowForge-Secret") or request.query_params.get(
                "secret"
            )
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
        version.id, input_payload=payload, trigger_type="webhook", triggered_by=triggered_by
    )
    return Response(
        {"execution_id": str(execution.id), "status": "pending"},
        status=status.HTTP_202_ACCEPTED,
    )
