from django.contrib.auth import get_user_model

from apps.workflows.models import WorkflowVersion

from .models import Execution
from .tasks import execute_workflow


def start_execution(
    workflow_version_id,
    input_payload=None,
    triggered_by=None,
    trigger_type="manual",
) -> Execution:
    version = WorkflowVersion.objects.get(pk=workflow_version_id)
    execution = Execution.objects.create(
        workflow_version=version,
        status="pending",
        trigger_type=trigger_type,
        input_payload=input_payload or {},
        created_by=triggered_by,
    )
    execute_workflow.delay(str(execution.id))
    return execution
