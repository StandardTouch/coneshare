from rest_framework import serializers

from permissions_rbac.catalogue import (
    PERMISSION_DEFINITIONS,
    PERM_CREATE_DATAROOM,
    SITE_ROLE_ADMIN,
    SITE_ROLE_MEMBER,
    iter_dataroom_permission_definitions,
)
from permissions_rbac.models import DataroomRole, DataroomRolePermission, PermissionAuditLog, SiteRolePermission, DataroomFolderRoleRule


class DataroomRolePermissionSerializer(serializers.ModelSerializer):
    class Meta:
        model = DataroomRolePermission
        fields = ('permission', 'scope')


class DataroomRoleSerializer(serializers.ModelSerializer):
    permission_grants = DataroomRolePermissionSerializer(many=True, read_only=True)
    user_count = serializers.IntegerField(read_only=True, required=False)

    class Meta:
        model = DataroomRole
        fields = (
            'id',
            'slug',
            'name',
            'description',
            'is_system',
            'permission_grants',
            'user_count',
        )
        read_only_fields = ('id', 'slug', 'is_system')

    def validate_name(self, value):
        request = self.context.get('request')
        if not request:
            return value
        org = request.user.organization
        qs = DataroomRole.objects.filter(organization=org, name__iexact=value.strip())
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError(
                'A role with this name already exists in your organization.'
            )
        return value.strip()

    def validate_slug(self, value):
        if self.instance and self.instance.is_system:
            return self.instance.slug
        return value


class PermissionAuditLogSerializer(serializers.ModelSerializer):
    actor_email = serializers.EmailField(source='actor.email', read_only=True, default=None)

    class Meta:
        model = PermissionAuditLog
        fields = (
            'id',
            'created_at',
            'actor_email',
            'target_type',
            'target_id',
            'summary',
            'details',
        )


class DataroomFolderRoleRuleSerializer(serializers.ModelSerializer):
    dataroom_role_name = serializers.CharField(source='dataroom_role.name', read_only=True)

    class Meta:
        model = DataroomFolderRoleRule
        fields = ('id', 'dataroom_folder', 'dataroom_role', 'dataroom_role_name', 'rule')


class PermissionMatrixSerializer:
    @staticmethod
    def build(organization, roles_qs, request):
        permissions = [
            {
                'codename': d.codename,
                'label': d.label,
                'supports_scope': d.supports_scope,
                'category': d.category,
            }
            for d in iter_dataroom_permission_definitions()
        ]
        roles = DataroomRoleSerializer(roles_qs, many=True, context={'request': request}).data
        site_grants = {
            SITE_ROLE_ADMIN: list(
                SiteRolePermission.objects.filter(
                    organization=organization, site_role=SITE_ROLE_ADMIN
                ).values_list('permission', flat=True)
            ),
            SITE_ROLE_MEMBER: list(
                SiteRolePermission.objects.filter(
                    organization=organization, site_role=SITE_ROLE_MEMBER
                ).values_list('permission', flat=True)
            ),
        }
        return {
            'permissions': permissions,
            'roles': roles,
            'site_permissions': site_grants,
            'site_permission_definitions': [
                {
                    'codename': PERM_CREATE_DATAROOM,
                    'label': PERMISSION_DEFINITIONS[PERM_CREATE_DATAROOM].label,
                }
            ],
        }
