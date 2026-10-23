from django.contrib.auth import get_user_model

from rest_framework import serializers

from apps.workflows.models import Edge, Node, Workflow, WorkflowVersion

User = get_user_model()


class WorkflowSerializer(serializers.ModelSerializer):
    slug = serializers.SlugField(required=False, allow_blank=True)

    class Meta:
        model = Workflow
        fields = [
            "id",
            "name",
            "slug",
            "description",
            "is_active",
            "is_public",
            "created_by",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_by", "created_at", "updated_at"]

    def create(self, validated_data):
        if not validated_data.get("slug"):
            from django.utils.text import slugify

            validated_data["slug"] = slugify(validated_data["name"])
        return super().create(validated_data)


class WorkflowVersionSerializer(serializers.ModelSerializer):
    version_number = serializers.IntegerField(required=False)

    class Meta:
        model = WorkflowVersion
        fields = ["id", "workflow", "version_number", "is_published", "definition", "created_at"]
        read_only_fields = ["id", "workflow", "created_at"]


class NodeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Node
        fields = [
            "id",
            "workflow_version",
            "key",
            "name",
            "node_type",
            "config",
            "input_schema",
            "output_schema",
            "position_x",
            "position_y",
            "created_at",
        ]
        read_only_fields = ["id", "workflow_version", "created_at"]


class EdgeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Edge
        fields = [
            "id",
            "workflow_version",
            "source_node",
            "target_node",
            "source_handle",
            "target_handle",
            "condition",
            "created_at",
        ]
        read_only_fields = ["id", "workflow_version", "created_at"]

    def validate(self, attrs):
        source = attrs.get("source_node")
        target = attrs.get("target_node")
        version = self.context.get("workflow_version")
        if source and target:
            if source.workflow_version_id != target.workflow_version_id:
                raise serializers.ValidationError("Source and target must belong to the same version.")
            if version is not None and source.workflow_version_id != version.id:
                raise serializers.ValidationError("Nodes must belong to this version.")
        return attrs
