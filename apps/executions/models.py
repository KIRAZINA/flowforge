import uuid

from django.conf import settings
from django.db import models


class Execution(models.Model):
    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("running", "Running"),
        ("success", "Success"),
        ("failed", "Failed"),
        ("cancelled", "Cancelled"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    workflow_version = models.ForeignKey(
        "workflows.WorkflowVersion",
        on_delete=models.PROTECT,
        related_name="executions",
    )
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default="pending")
    trigger_type = models.CharField(max_length=50, blank=True)
    input_payload = models.JSONField(default=dict)
    output_payload = models.JSONField(default=dict, blank=True)
    error_message = models.TextField(blank=True)
    started_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="executions",
    )

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Execution"
        verbose_name_plural = "Executions"
        indexes = [
            models.Index(fields=["status", "created_at"]),
            models.Index(fields=["created_at"]),
            models.Index(fields=["workflow_version", "status"]),
        ]

    def __str__(self) -> str:
        return f"Execution {self.id} ({self.status})"

    @property
    def duration(self):
        if self.started_at and self.finished_at:
            return self.finished_at - self.started_at
        return None


class ExecutionLog(models.Model):
    LEVEL_CHOICES = [
        ("debug", "Debug"),
        ("info", "Info"),
        ("warning", "Warning"),
        ("error", "Error"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    execution = models.ForeignKey(
        Execution, on_delete=models.CASCADE, related_name="logs"
    )
    node = models.ForeignKey(
        "workflows.Node", on_delete=models.SET_NULL, null=True, blank=True
    )
    level = models.CharField(max_length=20, choices=LEVEL_CHOICES, default="info")
    message = models.TextField()
    data = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]
        verbose_name = "Execution Log"
        verbose_name_plural = "Execution Logs"
        indexes = [
            models.Index(fields=["execution", "level"]),
            models.Index(fields=["execution", "created_at"]),
            models.Index(fields=["created_at"]),
        ]

    def __str__(self) -> str:
        return f"{self.level.upper()}: {self.message[:50]}"
