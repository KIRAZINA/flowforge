import uuid

from django.conf import settings
from django.db import models


class Workflow(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255, unique=True)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    is_public = models.BooleanField(default=False)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="workflows",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Workflow"
        verbose_name_plural = "Workflows"
        indexes = [
            models.Index(fields=["slug"]),
            models.Index(fields=["created_at"]),
            models.Index(fields=["is_active"]),
        ]

    def __str__(self) -> str:
        return self.name


class WorkflowVersion(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    workflow = models.ForeignKey(
        Workflow, on_delete=models.CASCADE, related_name="versions"
    )
    version_number = models.PositiveIntegerField()
    is_published = models.BooleanField(default=False)
    definition = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-version_number"]
        verbose_name = "Workflow Version"
        verbose_name_plural = "Workflow Versions"
        constraints = [
            models.UniqueConstraint(
                fields=["workflow", "version_number"],
                name="unique_workflow_version_number",
            ),
        ]
        indexes = [
            models.Index(fields=["workflow", "version_number"]),
            models.Index(fields=["created_at"]),
        ]

    def __str__(self) -> str:
        return f"{self.workflow.name} v{self.version_number}"


NODE_TYPE_CHOICES = [
    ("trigger", "Trigger"),
    ("action", "Action"),
    ("transform", "Transform"),
    ("filter", "Filter"),
    ("condition", "Condition"),
    ("http_request", "HTTP Request"),
    ("webhook", "Webhook"),
    ("python", "Python"),
]


class Node(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    workflow_version = models.ForeignKey(
        WorkflowVersion, on_delete=models.CASCADE, related_name="nodes"
    )
    key = models.CharField(max_length=100)
    name = models.CharField(max_length=255)
    node_type = models.CharField(max_length=50, choices=NODE_TYPE_CHOICES)
    config = models.JSONField(default=dict)
    input_schema = models.JSONField(default=dict)
    output_schema = models.JSONField(default=dict)
    position_x = models.IntegerField(default=0)
    position_y = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]
        verbose_name = "Node"
        verbose_name_plural = "Nodes"
        constraints = [
            models.UniqueConstraint(
                fields=["workflow_version", "key"],
                name="unique_node_key_per_version",
            ),
        ]
        indexes = [
            models.Index(fields=["workflow_version", "node_type"]),
            models.Index(fields=["created_at"]),
        ]

    def __str__(self) -> str:
        return f"{self.name} ({self.key})"


class Edge(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    workflow_version = models.ForeignKey(
        WorkflowVersion, on_delete=models.CASCADE, related_name="edges"
    )
    source_node = models.ForeignKey(
        Node, on_delete=models.CASCADE, related_name="outgoing_edges"
    )
    target_node = models.ForeignKey(
        Node, on_delete=models.CASCADE, related_name="incoming_edges"
    )
    source_handle = models.CharField(max_length=100, blank=True, default="default")
    target_handle = models.CharField(max_length=100, blank=True, default="default")
    condition = models.JSONField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]
        verbose_name = "Edge"
        verbose_name_plural = "Edges"
        indexes = [
            models.Index(fields=["workflow_version"]),
            models.Index(fields=["source_node"]),
            models.Index(fields=["target_node"]),
        ]

    def __str__(self) -> str:
        return f"{self.source_node.key} -> {self.target_node.key}"


TRIGGER_TYPE_CHOICES = [
    ("webhook", "Webhook"),
    ("cron", "Cron"),
    ("manual", "Manual"),
]


class Trigger(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    workflow = models.ForeignKey(
        Workflow, on_delete=models.CASCADE, related_name="triggers"
    )
    trigger_type = models.CharField(max_length=50, choices=TRIGGER_TYPE_CHOICES)
    config = models.JSONField(default=dict)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Trigger"
        verbose_name_plural = "Triggers"
        indexes = [
            models.Index(fields=["workflow", "trigger_type"]),
            models.Index(fields=["is_active"]),
        ]

    def __str__(self) -> str:
        return f"{self.workflow.name} - {self.trigger_type}"
