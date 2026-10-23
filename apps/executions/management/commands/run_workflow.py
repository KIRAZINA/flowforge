from django.core.management.base import BaseCommand

from apps.executions.models import Execution
from apps.executions.services import start_execution


class Command(BaseCommand):
    help = "Start an asynchronous workflow execution by workflow version id"

    def add_arguments(self, parser):
        parser.add_argument("workflow_version_id")
        parser.add_argument("--input", default="{}")

    def handle(self, *args, **options):
        import json

        payload = json.loads(options["input"])
        execution = start_execution(options["workflow_version_id"], input_payload=payload)
        self.stdout.write(self.style.SUCCESS(f"Started execution {execution.id}"))
