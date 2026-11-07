"""Admin user serializer helpers for unified organization RBAC roles."""
from django.contrib.auth import get_user_model
from rest_framework import serializers

from permissions_rbac.models import DataroomRole

User = get_user_model()


class OrganizationRoleNestedSerializer(serializers.Serializer):
    id = serializers.CharField()
    name = serializers.CharField()
    slug = serializers.CharField()
    is_system = serializers.BooleanField()


class OrganizationRoleAdminUserMixin:
    """Adds organization_role read/write fields to AdminUserSerializer."""

    @staticmethod
    def extract_organization_role_side_effects(validated_data):
        role_id = validated_data.pop('_organization_role_id', serializers.empty)
        clear_role = validated_data.pop('_clear_organization_role', False)
        return role_id, clear_role

    @staticmethod
    def apply_organization_role_side_effects(user, organization_role_id, clear_role=False):
        if clear_role:
            user.organization_role = None
            user.save(update_fields=['organization_role', 'updated_at'])
            return user
        if organization_role_id is not serializers.empty:
            if organization_role_id:
                role = DataroomRole.objects.filter(
                    id=organization_role_id,
                    organization_id=user.organization_id,
                ).first()
                if role:
                    user.organization_role = role
                    user.save(update_fields=['organization_role', 'updated_at'])
            else:
                user.organization_role = None
                user.save(update_fields=['organization_role', 'updated_at'])
        return user

    def get_fields(self):
        fields = super().get_fields()
        fields['organization_role'] = OrganizationRoleNestedSerializer(read_only=True, required=False)
        fields['organization_role_id'] = serializers.CharField(
            write_only=True,
            required=False,
            allow_null=True,
            allow_blank=True,
        )
        # Deprecated; kept read-only for clients still expecting role labels during transition.
        fields['role_label'] = serializers.SerializerMethodField(read_only=True)
        fields['role_label_id'] = serializers.CharField(
            write_only=True,
            required=False,
            allow_null=True,
            allow_blank=True,
        )
        return fields

    def get_role_label(self, instance):
        role = getattr(instance, 'organization_role', None)
        if role:
            return {'id': str(role.id), 'name': role.name}
        return None

    def to_representation(self, instance):
        data = super().to_representation(instance)
        role = getattr(instance, 'organization_role', None)
        if role:
            data['organization_role'] = OrganizationRoleNestedSerializer(
                {
                    'id': str(role.id),
                    'name': role.name,
                    'slug': role.slug,
                    'is_system': role.is_system,
                }
            ).data
        else:
            data['organization_role'] = None
        return data

    def validate(self, attrs):
        attrs = super().validate(attrs)
        organization = self.context['request'].user.organization

        organization_role_id = attrs.pop('organization_role_id', serializers.empty)
        legacy_label_id = attrs.pop('role_label_id', serializers.empty)
        if organization_role_id is serializers.empty and legacy_label_id is not serializers.empty:
            organization_role_id = legacy_label_id

        role = attrs.get('role')
        if role is None and self.instance is not None:
            role = self.instance.role

        if organization_role_id is not serializers.empty and organization_role_id:
            if role == 'admin':
                raise serializers.ValidationError(
                    {'organization_role_id': 'Organization administrators cannot have an assigned RBAC role.'}
                )
            attrs['role'] = 'member'
            if not DataroomRole.objects.filter(id=organization_role_id, organization=organization).exists():
                raise serializers.ValidationError(
                    {'organization_role_id': 'Invalid organization role for this organization.'}
                )
            attrs['_organization_role_id'] = organization_role_id
        elif role == 'admin':
            attrs['_clear_organization_role'] = True
        elif organization_role_id is not serializers.empty and organization_role_id in (None, ''):
            attrs['_clear_organization_role'] = True

        return attrs
