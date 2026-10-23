import pytest
from django.contrib.auth import get_user_model

from apps.executions.models import Execution, ExecutionLog
from apps.executions.runner import SyncDAGRunner, run_workflow_sync
from apps.workflows.models import Edge, Node, Workflow, WorkflowVersion

User = get_user_model()


@pytest.fixture
def user(db):
    return User.objects.create_user("runner", "runner@example.com", "pass")


@pytest.fixture
def version(user):
    workflow = Workflow.objects.create(name="W", slug="w", created_by=user)
    version = WorkflowVersion.objects.create(workflow=workflow, version_number=1, is_published=True)
    return workflow, version


def make_node(version, key, node_type, config=None, name=None):
    return Node.objects.create(
        workflow_version=version,
        key=key,
        name=name or key,
        node_type=node_type,
        config=config or {},
    )


@pytest.mark.django_db
def test_linear_workflow(version):
    workflow, ver = version
    n1 = make_node(ver, "a", "transform", {"code": "result = {'a': data['x'] + 1}"})
    n2 = make_node(ver, "b", "transform", {"code": "result = {'b': data['a'] * 2}"})
    n3 = make_node(ver, "c", "transform", {"code": "result = {'c': data['b'] + 3}"})
    Edge.objects.create(workflow_version=ver, source_node=n1, target_node=n2)
    Edge.objects.create(workflow_version=ver, source_node=n2, target_node=n3)

    execution = Execution.objects.create(workflow_version=ver, input_payload={"x": 5})
    run = SyncDAGRunner(execution).run()
    assert run.status == "success"
    assert run.output_payload["c"] == 15


@pytest.mark.django_db
def test_branching_workflow(version):
    workflow, ver = version
    a = make_node(ver, "a", "transform", {"code": "result = {'a': data['x'] + 1}"})
    b = make_node(ver, "b", "transform", {"code": "result = {'b': data['x'] * 2}"})
    c = make_node(ver, "c", "transform", {"code": "result = {'total': data['a'] + data['b']}"})
    Edge.objects.create(workflow_version=ver, source_node=a, target_node=c)
    Edge.objects.create(workflow_version=ver, source_node=b, target_node=c)

    execution = Execution.objects.create(workflow_version=ver, input_payload={"x": 5})
    run = run_workflow_sync(execution)
    assert run.status == "success"
    assert run.output_payload["total"] == 16


@pytest.mark.django_db
def test_cycle_detection(version):
    workflow, ver = version
    a = make_node(ver, "a", "transform", {"code": "result = data"})
    b = make_node(ver, "b", "transform", {"code": "result = data"})
    Edge.objects.create(workflow_version=ver, source_node=a, target_node=b)
    Edge.objects.create(workflow_version=ver, source_node=b, target_node=a)

    execution = Execution.objects.create(workflow_version=ver, input_payload={})
    run = SyncDAGRunner(execution).run()
    assert run.status == "failed"
    assert "cycle" in run.error_message.lower()


@pytest.mark.django_db
def test_transform_failure(version):
    workflow, ver = version
    _node = make_node(ver, "a", "transform", {"code": "result = 1 / 0"})
    execution = Execution.objects.create(workflow_version=ver, input_payload={})
    run = SyncDAGRunner(execution).run()
    assert run.status == "failed"
    assert "ZeroDivisionError" in run.error_message


@pytest.mark.django_db
def test_creates_execution_logs(version):
    workflow, ver = version
    _node = make_node(ver, "a", "transform", {"code": "result = {'ok': True}"})
    execution = Execution.objects.create(workflow_version=ver, input_payload={})
    SyncDAGRunner(execution).run()
    assert ExecutionLog.objects.filter(execution=execution).count() >= 2


@pytest.mark.django_db
def test_filter_node(version):
    workflow, ver = version
    _node = make_node(ver, "f", "filter", {"condition": "data['status'] == 'active'"})
    execution = Execution.objects.create(workflow_version=ver, input_payload={"status": "active"})
    run = SyncDAGRunner(execution).run()
    assert run.status == "success"
    assert run.output_payload.get("_filter_passed") is True
