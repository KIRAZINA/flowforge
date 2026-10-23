import pytest
from django.contrib.auth import get_user_model
from django.test import override_settings
from rest_framework.test import APIClient

from apps.executions.models import Execution
from apps.workflows.models import Trigger, Workflow, WorkflowVersion
from apps.workflows.models import Node

User = get_user_model()


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def published_workflow(db):
    user = User.objects.create_user("webuser", "web@example.com", "pass")
    workflow = Workflow.objects.create(name="HookFlow", slug="hook-flow", is_active=True, created_by=user)
    version = WorkflowVersion.objects.create(workflow=workflow, version_number=1, is_published=True)
    Node.objects.create(
        workflow_version=version,
        key="t",
        name="t",
        node_type="transform",
        config={"code": "result = {'ok': True}"},
    )
    return workflow, version


@pytest.mark.django_db
@override_settings(CELERY_TASK_ALWAYS_EAGER=True, CELERY_TASK_EAGER_PROPAGATES=True)
def test_webhook_success(api_client, published_workflow):
    workflow, version = published_workflow
    response = api_client.post("/hooks/hook-flow/", {"x": 1}, format="json")
    assert response.status_code == 202
    assert "execution_id" in response.data
    execution = Execution.objects.get(pk=response.data["execution_id"])
    assert execution.status == "success"


@pytest.mark.django_db
def test_webhook_workflow_not_found(api_client):
    response = api_client.post("/hooks/missing-flow/", {}, format="json")
    assert response.status_code == 404


@pytest.mark.django_db
def test_webhook_no_published_version(api_client, published_workflow):
    workflow, version = published_workflow
    version.is_published = False
    version.save()
    response = api_client.post("/hooks/hook-flow/", {}, format="json")
    assert response.status_code == 409


@pytest.mark.django_db
@override_settings(CELERY_TASK_ALWAYS_EAGER=True, CELERY_TASK_EAGER_PROPAGATES=True)
def test_webhook_invalid_secret(api_client, published_workflow):
    workflow, version = published_workflow
    Trigger.objects.create(
        workflow=workflow,
        trigger_type="webhook",
        is_active=True,
        config={"secret": "topsecret"},
    )
    response = api_client.post(
        "/hooks/hook-flow/", {}, format="json", HTTP_X_FLOWFORGE_SECRET="wrong"
    )
    assert response.status_code == 403


@pytest.mark.django_db
@override_settings(CELERY_TASK_ALWAYS_EAGER=True, CELERY_TASK_EAGER_PROPAGATES=True)
def test_webhook_wrong_method(api_client, published_workflow):
    workflow, version = published_workflow
    Trigger.objects.create(
        workflow=workflow,
        trigger_type="webhook",
        is_active=True,
        config={"methods": ["POST"]},
    )
    response = api_client.get("/hooks/hook-flow/")
    assert response.status_code == 405
