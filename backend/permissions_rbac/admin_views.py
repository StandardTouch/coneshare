"""Admin API for dataroom RBAC configuration."""
from django.db import transaction
from django.db.models import Count
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from core.permissions import IsAdmin
from permissions_rbac.audit import log_permission_change
from permissions_rbac.catalogue import (
    PERMISSION_DEFINITIONS,
    PERM_CREATE_DATAROOM,
    SYSTEM_ROLE_SLUGS,
    iter_dataroom_permission_definitions,
)
from permissions_rbac.models import DataroomRole, DataroomRolePermission, PermissionAuditLog, SiteRolePermission
from permissions_rbac.seed import ensure_default_roles_for_organization, reset_all_system_roles_for_organization
from permissions_rbac.serializers import (
    DataroomRoleSerializer,
    PermissionAuditLogSerializer,
    PermissionMatrixSerializer,
)
from permissions_rbac.services import invalidate_organization_rbac_cache


class AdminDataroomRoleViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAdmin]
    serializer_class = DataroomRoleSerializer

    def get_queryset(self):
        org = self.request.user.organization
        return (
            DataroomRole.objects.filter(organization=org)
            .annotate(user_count=Count('collaborators'))
            .prefetch_related('permission_grants')
            .order_by('name')
        )

    def perform_create(self, serializer):
        role = serializer.save(organization=self.request.user.organization, is_system=False)
        log_permission_change(
            self.request.user,
            PermissionAuditLog.TARGET_ROLE,
            str(role.id),
            f'Created custom role {role.name}',
            {'slug': role.slug},
        )
        invalidate_organization_rbac_cache(str(self.request.user.organization_id))

    def perform_update(self, serializer):
        role = serializer.instance
        if role.is_system and 'slug' in serializer.validated_data:
            serializer.validated_data.pop('slug', None)
        if role.is_system and 'name' in serializer.validated_data:
            serializer.validated_data.pop('name', None)
        updated = serializer.save()
        log_permission_change(
            self.request.user,
            PermissionAuditLog.TARGET_ROLE,
            str(updated.id),
            f'Updated role {updated.name}',
            {},
        )
        invalidate_organization_rbac_cache(str(self.request.user.organization_id))

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        if instance.is_system:
            return Response({'detail': 'System roles cannot be deleted.'}, status=status.HTTP_400_BAD_REQUEST)
        if instance.collaborators.exists():
            return Response(
                {'detail': 'Reassign collaborators before deleting this role.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        role_id = str(instance.id)
        name = instance.name
        org_id = str(request.user.organization_id)
        instance.delete()
        log_permission_change(
            request.user,
            PermissionAuditLog.TARGET_ROLE,
            role_id,
            f'Deleted role {name}',
            {},
        )
        invalidate_organization_rbac_cache(org_id)
        return Response(status=status.HTTP_204_NO_CONTENT)

    def perform_destroy(self, instance):
        pass

    @action(detail=False, methods=['get'], url_path='matrix')
    def matrix(self, request):
        org = request.user.organization
        ensure_default_roles_for_organization(org)
        roles = self.get_queryset()
        payload = PermissionMatrixSerializer.build(org, roles, request)
        return Response(payload)

    @action(detail=True, methods=['put'], url_path='permissions')
    def set_permissions(self, request, pk=None):
        role = self.get_object()
        grants = request.data.get('grants') or []
        with transaction.atomic():
            DataroomRolePermission.objects.filter(role=role).delete()
            rows = []
            for entry in grants:
                permission = entry.get('permission')
                if permission not in PERMISSION_DEFINITIONS:
                    continue
                scope = entry.get('scope') or ''
                rows.append(
                    DataroomRolePermission(role=role, permission=permission, scope=scope)
                )
            if rows:
                DataroomRolePermission.objects.bulk_create(rows)
        log_permission_change(
            request.user,
            PermissionAuditLog.TARGET_ROLE,
            str(role.id),
            f'Updated permissions for role {role.name}',
            {'grants': grants},
        )
        invalidate_organization_rbac_cache(str(request.user.organization_id))
        return Response({'status': 'ok'})

    @action(detail=False, methods=['post'], url_path='reset-defaults')
    def reset_defaults(self, request):
        org = request.user.organization
        reset_all_system_roles_for_organization(org)
        log_permission_change(
            request.user,
            PermissionAuditLog.TARGET_ROLE,
            '',
            'Reset system roles to defaults',
            {},
        )
        invalidate_organization_rbac_cache(str(org.id))
        return Response({'status': 'ok'})

    @action(detail=False, methods=['put'], url_path='site-permissions')
    def set_site_permissions(self, request):
        org = request.user.organization
        site_role = request.data.get('site_role')
        permissions = request.data.get('permissions') or []
        if site_role not in ('admin', 'member'):
            return Response({'detail': 'Invalid site_role.'}, status=status.HTTP_400_BAD_REQUEST)
        allowed = {PERM_CREATE_DATAROOM}
        with transaction.atomic():
            SiteRolePermission.objects.filter(organization=org, site_role=site_role).delete()
            for perm in permissions:
                if perm in allowed:
                    SiteRolePermission.objects.create(
                        organization=org,
                        site_role=site_role,
                        permission=perm,
                    )
        log_permission_change(
            request.user,
            PermissionAuditLog.TARGET_SITE,
            site_role,
            f'Updated site permissions for {site_role}',
            {'permissions': permissions},
        )
        invalidate_organization_rbac_cache(str(org.id))
        return Response({'status': 'ok'})


class AdminPermissionAuditLogViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    permission_classes = [IsAdmin]
    serializer_class = PermissionAuditLogSerializer

    def get_queryset(self):
        return PermissionAuditLog.objects.filter(
            organization=self.request.user.organization
        ).select_related('actor')[:200]
