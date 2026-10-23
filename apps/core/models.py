import hashlib
import hmac
import secrets
import uuid

from django.conf import settings
from django.db import models
from django.utils import timezone


class ApiKey(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="api_keys"
    )
    name = models.CharField(max_length=100)
    key = models.CharField(max_length=64, unique=True)  # SHA-256 hash of the raw key
    prefix = models.CharField(max_length=12)
    is_active = models.BooleanField(default=True)
    last_used_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "API Key"
        verbose_name_plural = "API Keys"
        indexes = [
            models.Index(fields=["prefix", "is_active"]),
            models.Index(fields=["user"]),
        ]

    def __str__(self) -> str:
        return f"{self.name} ({self.prefix})"

    @classmethod
    def create_key(cls, user, name, expires_at=None):
        raw_key = f"ff_live_{secrets.token_urlsafe(32)}"
        prefix = raw_key[:12]
        key_hash = hashlib.sha256(raw_key.encode("utf-8")).hexdigest()
        instance = cls.objects.create(
            user=user, name=name, key=key_hash, prefix=prefix, expires_at=expires_at
        )
        return instance, raw_key

    def verify(self, raw_key: str) -> bool:
        if not self.is_active:
            return False
        if self.expires_at and self.expires_at < timezone.now():
            return False
        expected = hashlib.sha256(raw_key.encode("utf-8")).hexdigest()
        return hmac.compare_digest(self.key, expected)
