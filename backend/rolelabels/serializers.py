from django.contrib.auth import get_user_model
from django.db import transaction
from rest_framework import serializers

from .models import RoleLabel
from .services import clear_user_role_label, get_user_role_label, role_labels_enabled, set_user_role_label

User = get_user_model()


class RoleLabelSerializer(serializers.ModelSerializer):
    user_count = serializers.SerializerMethodField(read_only=True)
    is_system = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = RoleLabel
        fields = ['id', 'name', 'description', 'user_count', 'is_system', 'created_at', 'updated_at']
        read_only_fields = ['id', 'user_count', 'is_system', 'created_at', 'updated_at']

    def get_user_count(self, obj):
        if getattr(obj, '_user_count', None) is not None:
            return obj._user_count
        return obj.user_assignments.count()

    def get_is_system(self, obj):
        return False

    def validate_name(self, value):
        name = (value or '').strip()
        if not name:
            raise serializers.ValidationError('Name is required.')
        organization = self.context['request'].user.organization
        qs = RoleLabel.objects.filter(organization=organization, name__iexact=name)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError('A role with this name already exists in your organization.')
        return name


class RoleLabelNestedSerializer(serializers.ModelSerializer):
    class Meta:
        model = RoleLabel
        fields = ['id', 'name']


class RoleLabelAdminUserMixin:
    """Adds role_label read/write fields to AdminUserSerializer."""

    @staticmethod
    def extract_role_label_side_effects(validated_data):
        """Remove mixin-internal keys before User.create_user / model update kwargs."""
        role_label_id = validated_data.pop('_role_label_id', serializers.empty)
        clear_label = validated_data.pop('_clear_role_label', False)
        return role_label_id, clear_label

    @staticmethod
    def apply_role_label_side_effects(user, role_label_id, clear_label=False):
        if not role_labels_enabled():
            return user
        if clear_label:
            clear_user_role_label(user)
        elif role_label_id is not serializers.empty and role_label_id:
            set_user_role_label(user, role_label_id)
        return user

    @staticmethod
    def apply_role_label_changes(user, validated_data):
        role_label_id, clear_label = RoleLabelAdminUserMixin.extract_role_label_side_effects(
            validated_data
        )
        return RoleLabelAdminUserMixin.apply_role_label_side_effects(
            user, role_label_id, clear_label
        )

    def get_fields(self):
        fields = super().get_fields()
        if role_labels_enabled():
            fields['role_label'] = RoleLabelNestedSerializer(read_only=True, allow_null=True, required=False)
            fields['role_label_id'] = serializers.CharField(
                write_only=True,
                required=False,
                allow_null=True,
                allow_blank=True,
            )
        return fields

    def to_representation(self, instance):
        data = super().to_representation(instance)
        if not role_labels_enabled():
            data.pop('role_label', None)
            return data
        label = get_user_role_label(instance)
        data['role_label'] = RoleLabelNestedSerializer(label).data if label else None
        return data

    def validate(self, attrs):
        attrs = super().validate(attrs)
        if not role_labels_enabled():
            attrs.pop('role_label_id', None)
            return attrs

        role_label_id = attrs.pop('role_label_id', serializers.empty)
        if role_label_id == '':
            role_label_id = None

        role = attrs.get('role')
        if role is None and self.instance is not None:
            role = self.instance.role

        if role_label_id is not serializers.empty and role_label_id:
            attrs['role'] = 'member'
            organization = self.context['request'].user.organization
            if not RoleLabel.objects.filter(id=role_label_id, organization=organization).exists():
                raise serializers.ValidationError({'role_label_id': 'Invalid role label for this organization.'})
            attrs['_role_label_id'] = role_label_id
        elif role == 'admin':
            attrs['_clear_role_label'] = True
        elif role_label_id is not serializers.empty and role_label_id is None:
            attrs['_clear_role_label'] = True

        return attrs

    def create(self, validated_data):
        role_label_id, clear_label = self.extract_role_label_side_effects(validated_data)
        with transaction.atomic():
            user = super().create(validated_data)
            self.apply_role_label_side_effects(user, role_label_id, clear_label)
        return user
