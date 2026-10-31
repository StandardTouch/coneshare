from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import RoleLabelViewSet

router = DefaultRouter()
router.register(r'role-labels', RoleLabelViewSet, basename='admin-role-label')

urlpatterns = [
    path('', include(router.urls)),
]
