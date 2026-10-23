import pytest
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import override_settings
from rest_framework.test import APIClient

from apps.workflows.models import Workflow, WorkflowVersion

User = get_user_model()

THROTTLE_SETTINGS = {
    "DEFAULT_THROTTLE_RATES": {
        "webhook": "2/min",
        "api": "2/min",
    }
}


@pytest.fixture(autouse=True)
def clear_cache():
    cache.clear()
    yield
    cache.clear()


@pytest.fixture
def published_workflow(db):
    user = User.objects.create_user("rluser", "rl@example.com", "pass")
    workflow = Workflow.objects.create(
        name="RLFlow", slug="rl-flow", is_active=True, created_by=user
    )
    version = WorkflowVersion.objects.create(workflow=workflow, version_number=1, is_published=True)
    return workflow, version


@pytest.mark.django_db
@override_settings(CELERY_TASK_ALWAYS_EAGER=True, REST_FRAMEWORK=THROTTLE_SETTINGS)
def test_webhook_rate_limit(published_workflow):
    workflow, version = published_workflow
    client = APIClient()
    responses = [client.post("/hooks/rl-flow/", {}, format="json") for _ in range(3)]
    assert responses[0].status_code == 202
    assert responses[1].status_code == 202
    assert responses[2].status_code == 429


@pytest.mark.django_db
@override_settings(CELERY_TASK_ALWAYS_EAGER=True, REST_FRAMEWORK=THROTTLE_SETTINGS)
def test_api_rate_limit(db):
    user = User.objects.create_user("rlapi", "rlapi@example.com", "pass")
    client = APIClient()
    client.force_authenticate(user=user)
    responses = [client.get("/api/workflows/") for _ in range(3)]
    assert responses[0].status_code == 200
    assert responses[1].status_code == 200
    assert responses[2].status_code == 429
