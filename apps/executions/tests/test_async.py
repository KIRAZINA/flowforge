import json
import pytest
from django.contrib.auth import get_user_model
from django.test import override_settings

from apps.executions.models import Execution
from apps.executions.services import start_execution
from apps.workflows.models import Edge, Node, Workflow, WorkflowVersion

User = get_user_model()


@pytest.fixture
def user(db):
    return User.objects.create_user("asyncuser", "async@example.com", "pass")


@pytest.fixture
def version(user):
    workflow = Workflow.objects.create(name="AsyncW", slug="asyncw", created_by=user)
    version = WorkflowVersion.objects.create(workflow=workflow, version_number=1, is_published=True)
    n = Node.objects.create(
        workflow_version=version,
        key="t",
        name="t",
        node_type="transform",
        config={"code": "result = {'out': data['x'] + 1}"},
    )
    return version


@pytest.mark.django_db
@override_settings(CELERY_TASK_ALWAYS_EAGER=True, CELERY_TASK_EAGER_PROPAGATES=True)
def test_start_execution_creates_and_runs(version):
    execution = start_execution(version.id, input_payload={"x": 5})
    assert execution.status in ("pending", "success", "running")
    execution.refresh_from_db()
    assert execution.status == "success"
    assert execution.output_payload["out"] == 6


@pytest.mark.django_db
@override_settings(CELERY_TASK_ALWAYS_EAGER=True, CELERY_TASK_EAGER_PROPAGATES=True)
def test_execute_task_direct(version):
    execution = Execution.objects.create(workflow_version=version, input_payload={"x": 2})
    from apps.executions.tasks import execute_workflow

    execute_workflow(str(execution.id))
    execution.refresh_from_db()
    assert execution.status == "success"
    assert execution.output_payload["out"] == 3
