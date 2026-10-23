import hashlib
import hmac

from django.utils import timezone
from rest_framework import exceptions
from rest_framework.authentication import BaseAuthentication

from apps.core.models import ApiKey


class ApiKeyAuthentication(BaseAuthentication):
    def authenticate(self, request):
        raw_key = None
        auth_header = request.headers.get("Authorization", "")
        if auth_header.lower().startswith("api-key "):
            raw_key = auth_header.split(" ", 1)[1].strip()
        elif request.headers.get("X-API-Key"):
            raw_key = request.headers.get("X-API-Key").strip()

        if not raw_key:
            return None

        prefix = raw_key[:12]
        candidates = ApiKey.objects.filter(prefix=prefix, is_active=True).select_related("user")
        for api_key in candidates:
            if api_key.expires_at and api_key.expires_at < timezone.now():
                continue
            expected = hashlib.sha256(raw_key.encode("utf-8")).hexdigest()
            if hmac.compare_digest(api_key.key, expected):
                api_key.last_used_at = timezone.now()
                api_key.save(update_fields=["last_used_at"])
                return api_key.user, api_key

        raise exceptions.AuthenticationFailed("Invalid or expired API key.")

    def authenticate_header(self, request):
        return "Api-Key"
