from permissions_rbac.request_context import reset_rbac_request_state, restore_rbac_request_state


class RbacRequestCacheMiddleware:
    """Reset per-request RBAC caches at the start of each HTTP request."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        token = reset_rbac_request_state()
        try:
            return self.get_response(request)
        finally:
            restore_rbac_request_state(token)
