from jsonschema import Draft202012Validator

from apps.workflows.models import WorkflowVersion


def resolve_payload_schema(trigger, version: WorkflowVersion):
    """Resolve a JSON Schema for a webhook payload.

    Priority:
    1. ``trigger.config["input_schema"]`` if present
    2. ``input_schema`` of any active webhook trigger for the workflow
    3. ``input_schema`` of the first starting node (no incoming edges)
    4. ``None`` (skip validation)
    """
    if isinstance(getattr(trigger, "config", None), dict):
        schema = trigger.config.get("input_schema")
        if isinstance(schema, dict) and schema:
            return schema

    # Fall back to any active webhook trigger carrying a schema.
    try:
        from apps.workflows.models import Trigger

        for candidate in Trigger.objects.filter(
            workflow=version.workflow, trigger_type="webhook", is_active=True
        ):
            if isinstance(candidate.config, dict):
                schema = candidate.config.get("input_schema")
                if isinstance(schema, dict) and schema:
                    return schema
    except Exception:
        pass

    try:
        nodes = list(version.nodes.all())
        edges = list(version.edges.all())
    except Exception:
        return None

    target_ids = {edge.target_node_id for edge in edges}
    starting_nodes = [node for node in nodes if node.id not in target_ids]
    for node in starting_nodes:
        schema = getattr(node, "input_schema", None)
        if isinstance(schema, dict) and schema:
            return schema
    return None


def validate_payload(schema, payload):
    """Return a list of validation error messages (empty means valid)."""
    if not isinstance(schema, dict) or not schema:
        return []
    validator = Draft202012Validator(schema)
    errors = sorted(validator.iter_errors(payload), key=lambda error: list(error.path))
    return [error.message for error in errors]
