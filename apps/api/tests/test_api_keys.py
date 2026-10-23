import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.test import APIClient

from apps.core.models import ApiKey
from apps.workflows.models import Workflow

User = get_user_model()


@pytest.fixture
def two_users(db):
    owner = User.objects.create_user("owner", "owner@example.com", "pass")
    other = User.objects.create_user("other", "other@example.com", "pass")
    return owner, other


def test_create_api_key(two_users):
    owner, _ = two_users
    api_key, raw = ApiKey.create_key(owner, "test")
    assert raw.startswith("ff_live_")
    assert api_key.prefix == raw[:12]
    assert api_key.verify(raw) is True
    assert api_key.verify("wrong") is False


def test_api_key_expired(two_users):
    owner, _ = two_users
    api_key, raw = ApiKey.create_key(
        owner, "expired", expires_at=timezone.now() - timezone.timedelta(days=1)
    )
    assert api_key.verify(raw) is False


def test_api_key_inactive(two_users):
    owner, _ = two_users
    api_key, raw = ApiKey.create_key(owner, "inactive")
    api_key.is_active = False
    api_key.save()
    assert api_key.verify(raw) is False


@pytest.mark.django_db
def test_authenticate_valid_key(two_users):
    owner, _ = two_users
    api_key, raw = ApiKey.create_key(owner, "valid")
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Api-Key {raw}")
    response = client.get("/api/workflows/")
    assert response.status_code == 200


@pytest.mark.django_db
def test_authenticate_invalid_key(two_users):
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION="Api-Key ff_live_invalid")
    response = client.get("/api/workflows/")
    assert response.status_code == 401


@pytest.mark.django_db
def test_owner_can_edit_workflow_other_cannot(two_users):
    owner, other = two_users
    _workflow = Workflow.objects.create(name="Owned", slug="owned", created_by=owner)
    owner_client = APIClient()
    owner_client.force_authenticate(user=owner)
    other_client = APIClient()
    other_client.force_authenticate(user=other)

    resp_owner = owner_client.patch(
        "/api/workflows/owned/", {"description": "updated"}, format="json"
    )
    assert resp_owner.status_code == 200

    resp_other = other_client.patch(
        "/api/workflows/owned/", {"description": "hacked"}, format="json"
    )
    assert resp_other.status_code == 403
