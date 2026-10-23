import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

User = get_user_model()


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def auth_client(db):
    user = User.objects.create_user("apiuser", "api@example.com", "pass")
    client = APIClient()
    client.force_authenticate(user=user)
    return client, user


@pytest.mark.django_db
def test_create_workflow(auth_client):
    client, user = auth_client
    response = client.post(
        "/api/workflows/", {"name": "My Flow", "description": "desc"}, format="json"
    )
    assert response.status_code == 201
    assert response.data["slug"] == "my-flow"


@pytest.mark.django_db
def test_retrieve_workflow(auth_client):
    client, user = auth_client
    client.post("/api/workflows/", {"name": "Retrieve Flow"}, format="json")
    response = client.get("/api/workflows/retrieve-flow/")
    assert response.status_code == 200
    assert response.data["name"] == "Retrieve Flow"


@pytest.mark.django_db
def test_full_workflow_happy_path(auth_client):
    client, user = auth_client
    wf_resp = client.post("/api/workflows/", {"name": "Full Flow"}, format="json")
    slug = wf_resp.data["slug"]
    version_resp = client.post(f"/api/workflows/{slug}/versions/", {}, format="json")
    assert version_resp.status_code == 201
    version_id = version_resp.data["id"]
    node1 = client.post(
        f"/api/workflows/{slug}/versions/{version_id}/nodes/",
        {
            "key": "a",
            "name": "A",
            "node_type": "transform",
            "config": {"code": "result = {'x': 1}"},
        },
        format="json",
    )
    node2 = client.post(
        f"/api/workflows/{slug}/versions/{version_id}/nodes/",
        {
            "key": "b",
            "name": "B",
            "node_type": "transform",
            "config": {"code": "result = {'y': 2}"},
        },
        format="json",
    )
    assert node1.status_code == 201 and node2.status_code == 201
    edge = client.post(
        f"/api/workflows/{slug}/versions/{version_id}/edges/",
        {"source_node": node1.data["id"], "target_node": node2.data["id"]},
        format="json",
    )
    assert edge.status_code == 201
    publish = client.post(f"/api/workflows/{slug}/versions/{version_id}/publish/")
    assert publish.status_code == 200
    assert publish.data["is_published"] is True


@pytest.mark.django_db
def test_schema_and_docs_available(api_client):
    schema = api_client.get("/api/schema/")
    docs = api_client.get("/api/docs/")
    assert schema.status_code == 200
    assert docs.status_code == 200
