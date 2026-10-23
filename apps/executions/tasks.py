import logging

from celery import shared_task
from django.utils import timezone

from apps.executions.models import Execution
from apps.executions.runner import SyncDAGRunner

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=30)
def execute_workflow(self, execution_id: str):
    try:
        execution = Execution.objects.select_related("workflow_version").get(pk=execution_id)
    except Execution.DoesNotExist:
        logger.warning("Execution %s does not exist", execution_id)
        return

    execution.status = "running"
    execution.started_at = timezone.now()
    execution.save(update_fields=["status", "started_at"])

    try:
        SyncDAGRunner(execution).run()
        execution.refresh_from_db()
        return str(execution.id)
    except Exception as exc:
        logger.exception("Unexpected error while executing %s", execution_id)
        execution.refresh_from_db()
        if execution.status not in ("success", "failed"):
            execution.status = "failed"
            execution.error_message = str(exc)
            execution.finished_at = timezone.now()
            execution.save(
                update_fields=["status", "error_message", "finished_at", "output_payload"]
            )
        try:
            raise self.retry(exc=exc)
        except self.MaxRetriesExceededError:
            execution.refresh_from_db()
            execution.status = "failed"
            execution.error_message = str(exc)
            execution.finished_at = timezone.now()
            execution.save(
                update_fields=["status", "error_message", "finished_at", "output_payload"]
            )
            return str(execution.id)
