from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .admin_views import AdminDataroomRoleViewSet, AdminPermissionAuditLogViewSet

router = DefaultRouter()
router.register(r'rbac/roles', AdminDataroomRoleViewSet, basename='admin-rbac-role')
router.register(r'rbac/audit-log', AdminPermissionAuditLogViewSet, basename='admin-rbac-audit')

urlpatterns = [
    path('', include(router.urls)),
]
