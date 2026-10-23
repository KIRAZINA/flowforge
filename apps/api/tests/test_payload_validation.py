import pytest
from django.contrib.auth import get_user_model
from django.test import override_settings
from rest_framework.test import APIClient

from apps.workflows.models import Node, Workflow, WorkflowVersion

User = get_user_model()


@pytest.fixture
def published_workflow_with_schema(db):
    user = User.objects.create_user("schemauser", "schema@example.com", "pass")
    workflow = Workflow.objects.create(
        name="SchemaFlow", slug="schema-flow", is_active=True, created_by=user
    )
    version = WorkflowVersion.objects.create(workflow=workflow, version_number=1, is_published=True)
    Node.objects.create(
        workflow_version=version,
        key="start",
        name="start",
        node_type="transform",
        config={"code": "result = data"},
        input_schema={
            "type": "object",
            "properties": {"name": {"type": "string"}, "age": {"type": "integer"}},
            "required": ["name"],
        },
    )
    return workflow, version


@pytest.fixture
def published_workflow_no_schema(db):
    user = User.objects.create_user("noschema", "noschema@example.com", "pass")
    workflow = Workflow.objects.create(
        name="NoSchemaFlow", slug="noschema-flow", is_active=True, created_by=user
    )
    version = WorkflowVersion.objects.create(workflow=workflow, version_number=1, is_published=True)
    return workflow, version


@pytest.mark.django_db
@override_settings(CELERY_TASK_ALWAYS_EAGER=True)
def test_valid_payload_against_schema(published_workflow_with_schema):
    client = APIClient()
    response = client.post("/hooks/schema-flow/", {"name": "Ada", "age": 30}, format="json")
    assert response.status_code == 202


@pytest.mark.django_db
@override_settings(CELERY_TASK_ALWAYS_EAGER=True)
def test_invalid_payload_against_schema(published_workflow_with_schema):
    client = APIClient()
    response = client.post("/hooks/schema-flow/", {"age": "old"}, format="json")
    assert response.status_code == 400
    assert response.data["error"] == "Payload validation failed"
    assert isinstance(response.data["details"], list)
    assert len(response.data["details"]) > 0


@pytest.mark.django_db
@override_settings(CELERY_TASK_ALWAYS_EAGER=True)
def test_no_schema_accepts_any_payload(published_workflow_no_schema):
    client = APIClient()
    response = client.post("/hooks/noschema-flow/", {"anything": [1, 2, 3]}, format="json")
    assert response.status_code == 202


@pytest.mark.django_db
@override_settings(CELERY_TASK_ALWAYS_EAGER=True)
def test_nested_schema_validation(published_workflow_with_schema):
    # Add trigger-level schema with nested object
    from apps.workflows.models import Trigger

    workflow, version = published_workflow_with_schema
    Trigger.objects.create(
        workflow=workflow,
        trigger_type="webhook",
        is_active=True,
        config={
            "input_schema": {
                "type": "object",
                "properties": {
                    "user": {
                        "type": "object",
                        "properties": {"email": {"type": "string", "format": "email"}},
                        "required": ["email"],
                    }
                },
                "required": ["user"],
            }
        },
    )
    client = APIClient()
    ok = client.post("/hooks/schema-flow/", {"user": {"email": "a@b.com"}}, format="json")
    bad = client.post("/hooks/schema-flow/", {"user": {"email": 5}}, format="json")
    assert ok.status_code == 202
    assert bad.status_code == 400
