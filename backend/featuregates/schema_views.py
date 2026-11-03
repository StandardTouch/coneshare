from django.http import Http404
from drf_spectacular.views import SpectacularAPIView, SpectacularRedocView, SpectacularSwaggerView

from featuregates.services import swagger_enabled


class _SwaggerGateMixin:
    def dispatch(self, request, *args, **kwargs):
        if not swagger_enabled():
            raise Http404()
        return super().dispatch(request, *args, **kwargs)


class GatedSpectacularAPIView(_SwaggerGateMixin, SpectacularAPIView):
    pass


class GatedSpectacularSwaggerView(_SwaggerGateMixin, SpectacularSwaggerView):
    pass


class GatedSpectacularRedocView(_SwaggerGateMixin, SpectacularRedocView):
    pass
