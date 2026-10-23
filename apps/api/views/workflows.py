from django.db import transaction
from django.shortcuts import get_object_or_404
from rest_framework import viewsets
from rest_framework.permissions import (
    IsAuthenticated,  # Access control is enforced by IsOwnerOrReadOnly / IsWorkflowOwnerOrReadOnly
)
from rest_framework.response import Response

from apps.api.permissions import IsOwnerOrReadOnly, IsWorkflowOwnerOrReadOnly
from apps.api.serializers import (
    EdgeSerializer,
    NodeSerializer,
    WorkflowSerializer,
    WorkflowVersionSerializer,
)
from apps.api.throttling import ApiRateThrottle
from apps.workflows.models import Edge, Node, Workflow, WorkflowVersion


class WorkflowViewSet(viewsets.ModelViewSet):
    queryset = Workflow.objects.all()
    serializer_class = WorkflowSerializer
    lookup_field = "slug"
    permission_classes = [IsAuthenticated, IsOwnerOrReadOnly]
    throttle_classes = [ApiRateThrottle]

    def perform_create(self, serializer):
        serializer.save(
            created_by=self.request.user if self.request.user.is_authenticated else None
        )


class WorkflowVersionViewSet(viewsets.ModelViewSet):
    serializer_class = WorkflowVersionSerializer
    lookup_field = "id"
    lookup_url_kwarg = "pk"
    permission_classes = [IsAuthenticated, IsWorkflowOwnerOrReadOnly]
    throttle_classes = [ApiRateThrottle]

    def get_queryset(self):
        queryset = WorkflowVersion.objects.all()
        slug = self.kwargs.get("slug")
        if slug:
            queryset = queryset.filter(workflow__slug=slug)
        return queryset

    def perform_create(self, serializer):
        workflow = get_object_or_404(Workflow, slug=self.kwargs["slug"])
        version_number = serializer.validated_data.get("version_number")
        if version_number is None:
            last = (
                WorkflowVersion.objects.filter(workflow=workflow)
                .order_by("-version_number")
                .first()
            )
            version_number = (last.version_number + 1) if last else 1
        serializer.save(workflow=workflow, version_number=version_number)

    @transaction.atomic
    def publish(self, request, pk=None, slug=None):
        version = self.get_object()
        version.is_published = True
        version.save(update_fields=["is_published"])
        WorkflowVersion.objects.filter(workflow=version.workflow).exclude(pk=version.pk).update(
            is_published=False
        )
        serializer = self.get_serializer(version)
        return Response(serializer.data, status=200)


class NodeViewSet(viewsets.ModelViewSet):
    serializer_class = NodeSerializer
    lookup_field = "id"
    lookup_url_kwarg = "pk"
    permission_classes = [IsAuthenticated, IsWorkflowOwnerOrReadOnly]
    throttle_classes = [ApiRateThrottle]

    def get_queryset(self):
        queryset = Node.objects.all()
        version_pk = self.kwargs.get("version_pk")
        if version_pk:
            queryset = queryset.filter(workflow_version_id=version_pk)
        slug = self.kwargs.get("slug")
        if slug:
            queryset = queryset.filter(workflow_version__workflow__slug=slug)
        return queryset

    def perform_create(self, serializer):
        version = get_object_or_404(WorkflowVersion, pk=self.kwargs["version_pk"])
        serializer.save(workflow_version=version)


class EdgeViewSet(viewsets.ModelViewSet):
    serializer_class = EdgeSerializer
    lookup_field = "id"
    lookup_url_kwarg = "pk"
    permission_classes = [IsAuthenticated, IsWorkflowOwnerOrReadOnly]
    throttle_classes = [ApiRateThrottle]

    def get_queryset(self):
        queryset = Edge.objects.all()
        version_pk = self.kwargs.get("version_pk")
        if version_pk:
            queryset = queryset.filter(workflow_version_id=version_pk)
        slug = self.kwargs.get("slug")
        if slug:
            queryset = queryset.filter(workflow_version__workflow__slug=slug)
        return queryset

    def perform_create(self, serializer):
        version = get_object_or_404(WorkflowVersion, pk=self.kwargs["version_pk"])
        serializer.save(workflow_version=version)

    def get_serializer_context(self):
        context = super().get_serializer_context()
        version_pk = self.kwargs.get("version_pk")
        if version_pk:
            try:
                context["workflow_version"] = WorkflowVersion.objects.get(pk=version_pk)
            except WorkflowVersion.DoesNotExist:
                pass
        return context
