from rest_framework.throttling import SimpleRateThrottle


class WebhookRateThrottle(SimpleRateThrottle):
    scope = "webhook"

    def get_cache_key(self, request, view):
        api_key = getattr(request, "auth", None)
        if api_key is not None and getattr(api_key, "prefix", None):
            ident = f"key:{api_key.prefix}"
        else:
            ident = self.get_ident(request)
        return self.cache_format % {"scope": self.scope, "ident": ident}


class ApiRateThrottle(SimpleRateThrottle):
    scope = "api"

    def get_cache_key(self, request, view):
        user = getattr(request, "user", None)
        api_key = getattr(request, "auth", None)
        if user is not None and getattr(user, "is_authenticated", False):
            ident = f"user:{user.pk}"
        elif api_key is not None and getattr(api_key, "prefix", None):
            ident = f"key:{api_key.prefix}"
        else:
            ident = self.get_ident(request)
        return self.cache_format % {"scope": self.scope, "ident": ident}
