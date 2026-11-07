from django.http import Http404
from drf_spectacular.views import SpectacularAPIView, SpectacularRedocView, SpectacularSwaggerView
from rest_framework.permissions import IsAuthenticated

from featuregates.services import ensure_swagger_for_user


class _SwaggerGateMixin:
    permission_classes = [IsAuthenticated]

    def dispatch(self, request, *args, **kwargs):
        if not getattr(request.user, 'is_authenticated', False):
            raise Http404()
        try:
            ensure_swagger_for_user(request.user)
        except Exception:
            raise Http404()
        return super().dispatch(request, *args, **kwargs)


class GatedSpectacularAPIView(_SwaggerGateMixin, SpectacularAPIView):
    pass


class GatedSpectacularSwaggerView(_SwaggerGateMixin, SpectacularSwaggerView):
    pass


class GatedSpectacularRedocView(_SwaggerGateMixin, SpectacularRedocView):
    pass
