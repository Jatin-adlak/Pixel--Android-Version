import hashlib
from collections.abc import Mapping

from rest_framework.throttling import SimpleRateThrottle


class CredentialThrottle(SimpleRateThrottle):
    scope = "credential"

    def get_cache_key(self, request, view):
        if request.method != "POST" or not isinstance(request.data, Mapping):
            return None
        identifier = request.data.get("identifier", request.data.get("email", ""))
        if not isinstance(identifier, str) or not identifier:
            return None
        identifier = identifier.strip().lower().removeprefix("@")[:254]
        key = hashlib.sha256(identifier.encode()).hexdigest()
        return self.cache_format % {"scope": self.scope, "ident": key}


class EmailCredentialThrottle(CredentialThrottle):
    scope = "email_account"
