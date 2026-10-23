from collections import deque

from django.utils import timezone

from apps.sandbox.executor import run_transform

from .models import Execution, ExecutionLog
from .realtime import broadcast_execution_log


class SyncDAGRunner:
    """Execute a workflow version synchronously in topological order."""

    def __init__(self, execution: Execution):
        self.execution = (
            Execution.objects.select_related("workflow_version__workflow")
            .prefetch_related(
                "workflow_version__nodes",
                "workflow_version__edges__source_node",
                "workflow_version__edges__target_node",
            )
            .get(pk=execution.pk)
        )

    def run(self) -> Execution:
        execution = self.execution
        execution.status = "running"
        execution.started_at = timezone.now()
        execution.save(update_fields=["status", "started_at"])

        try:
            version = execution.workflow_version
            nodes = list(version.nodes.all())
            edges = list(version.edges.all())
            node_by_id = {node.id: node for node in nodes}

            adjacency = {node.id: [] for node in nodes}
            in_degree = {node.id: 0 for node in nodes}
            for edge in edges:
                adjacency[edge.source_node_id].append(edge.target_node_id)
                in_degree[edge.target_node_id] += 1

            queue = deque(
                sorted(
                    (node for node in nodes if in_degree[node.id] == 0),
                    key=lambda item: item.created_at,
                )
            )
            ordered_ids = []
            while queue:
                current = queue.popleft()
                ordered_ids.append(current.id)
                for target_id in sorted(adjacency[current.id]):
                    in_degree[target_id] -= 1
                    if in_degree[target_id] == 0:
                        target_node = node_by_id[target_id]
                        queue.append(target_node)

            if len(ordered_ids) != len(nodes):
                raise ValueError("Cycle detected in workflow graph")

            context = {}
            if isinstance(execution.input_payload, dict):
                context.update(execution.input_payload)
            else:
                context["input"] = execution.input_payload

            for node_id in ordered_ids:
                node = node_by_id[node_id]
                started_log = ExecutionLog.objects.create(
                    execution=execution,
                    node=node,
                    level="info",
                    message=f"Node '{node.name}' started",
                    data={"node_type": node.node_type},
                )
                broadcast_execution_log(started_log)

                try:
                    if node.node_type in {"python", "transform"}:
                        code = node.config.get("code", "") if isinstance(node.config, dict) else ""
                        result = run_transform(code=code, data=context, timeout=5.0)
                        if not result.get("success"):
                            raise RuntimeError(result.get("error") or "Transform failed")
                        node_result = result.get("result")
                        stdout = result.get("stdout", "")
                    elif node.node_type == "filter":
                        condition = ""
                        if isinstance(node.config, dict):
                            condition = node.config.get("condition", "")
                        condition_result = self._evaluate_filter(condition, context)
                        node_result = {"_filter_passed": bool(condition_result)}
                        stdout = ""
                    else:
                        node_result = context
                        stdout = ""

                    if isinstance(node_result, dict):
                        context.update(node_result)
                    elif node_result is not None:
                        context[node.key] = node_result

                    completed_log = ExecutionLog.objects.create(
                        execution=execution,
                        node=node,
                        level="info",
                        message=f"Node '{node.name}' completed",
                        data={"result": node_result, "stdout": stdout},
                    )
                    broadcast_execution_log(completed_log)
                except Exception as exc:
                    failed_log = ExecutionLog.objects.create(
                        execution=execution,
                        node=node,
                        level="error",
                        message=f"Node '{node.name}' failed: {exc}",
                        data={"error": str(exc)},
                    )
                    broadcast_execution_log(failed_log)
                    raise

            execution.status = "success"
            execution.output_payload = context
            execution.finished_at = timezone.now()
            execution.save(
                update_fields=["status", "output_payload", "finished_at", "error_message"]
            )
            return execution
        except Exception as exc:
            execution.status = "failed"
            execution.error_message = str(exc)
            execution.finished_at = timezone.now()
            execution.save(
                update_fields=["status", "error_message", "finished_at", "output_payload"]
            )
            return execution

    @staticmethod
    def _evaluate_filter(condition: str, data: dict) -> bool:
        if not condition:
            return True
        # Simple, restricted evaluation for development use only.
        return bool(eval(condition, {"__builtins__": {}}, {"data": data}))  # noqa: S307


def run_workflow_sync(execution: Execution) -> Execution:
    return SyncDAGRunner(execution).run()
