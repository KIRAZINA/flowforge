from rest_framework.permissions import SAFE_METHODS, BasePermission


class IsOwnerOrReadOnly(BasePermission):
    def has_object_permission(self, request, view, obj):
        if request.method in SAFE_METHODS:
            return True
        user = request.user
        if getattr(user, "is_staff", False) or getattr(user, "is_superuser", False):
            return True
        return getattr(obj, "created_by", None) == user


class IsWorkflowOwnerOrReadOnly(BasePermission):
    def _workflow(self, obj):
        if hasattr(obj, "workflow"):
            return obj.workflow
        if hasattr(obj, "workflow_version"):
            return obj.workflow_version.workflow
        return None

    def has_object_permission(self, request, view, obj):
        if request.method in SAFE_METHODS:
            return True
        user = request.user
        if getattr(user, "is_staff", False) or getattr(user, "is_superuser", False):
            return True
        workflow = self._workflow(obj)
        return workflow is not None and workflow.created_by == user
