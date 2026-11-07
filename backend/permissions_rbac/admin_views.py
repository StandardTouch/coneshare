"""Admin API for dataroom RBAC configuration."""
from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models import Count, Q
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from core.pagination import StandardResultsSetPagination
from core.permissions import IsAdmin

User = get_user_model()
from permissions_rbac.audit import log_permission_change
from permissions_rbac.catalogue import (
    PERMISSION_DEFINITIONS,
    PERM_CREATE_DATAROOM,
    SYSTEM_ROLE_SLUGS,
    iter_role_grant_permission_definitions,
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
    pagination_class = StandardResultsSetPagination

    def get_queryset(self):
        org = self.request.user.organization
        qs = (
            DataroomRole.objects.filter(organization=org)
            .annotate(collaborator_count=Count('collaborators', distinct=True))
            .prefetch_related('permission_grants')
            .order_by('name')
        )
        search = (self.request.query_params.get('search') or '').strip()
        if search:
            qs = qs.filter(Q(name__icontains=search) | Q(slug__icontains=search))
        return qs

    def _attach_user_count(self, role):
        collab = getattr(role, 'collaborator_count', None)
        if collab is None:
            collab = role.collaborators.count()
        members = User.objects.filter(organization_role_id=role.id).count()
        role.user_count = collab + members
        return role

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        self._attach_user_count(instance)
        serializer = self.get_serializer(instance)
        return Response(serializer.data)

    def list(self, request, *args, **kwargs):
        ensure_default_roles_for_organization(request.user.organization)
        queryset = self.filter_queryset(self.get_queryset())
        org_member_counts = dict(
            User.objects.filter(organization=request.user.organization, organization_role__isnull=False)
            .values('organization_role_id')
            .annotate(c=Count('id'))
            .values_list('organization_role_id', 'c')
        )
        page = self.paginate_queryset(queryset)
        roles = page if page is not None else list(queryset)
        for role in roles:
            collab = getattr(role, 'collaborator_count', 0) or 0
            role.user_count = collab + org_member_counts.get(role.id, 0)
        serializer = self.get_serializer(roles, many=True)
        if page is not None:
            return self.get_paginated_response(serializer.data)
        return Response(serializer.data)

    def perform_create(self, serializer):
        from django.utils.text import slugify

        org = self.request.user.organization
        name = serializer.validated_data.get('name', '')
        base = slugify(name)[:32] or 'custom'
        slug = base
        n = 2
        while DataroomRole.objects.filter(organization=org, slug=slug).exists():
            suffix = f'-{n}'
            slug = f'{base[: max(1, 32 - len(suffix))]}{suffix}'
            n += 1
        role = serializer.save(organization=org, is_system=False, slug=slug)
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
        if instance.collaborators.exists() or User.objects.filter(organization_role=instance).exists():
            return Response(
                {'detail': 'Reassign users and collaborators before deleting this role.'},
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

    @action(detail=False, methods=['get'], url_path='permission-catalog')
    def permission_catalog(self, request):
        permissions = [
            {
                'codename': d.codename,
                'label': d.label,
                'supports_scope': d.supports_scope,
                'category': d.category,
                'group': d.group,
            }
            for d in iter_role_grant_permission_definitions()
        ]
        return Response({'permissions': permissions})

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
