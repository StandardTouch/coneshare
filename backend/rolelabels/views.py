from django.db.models import Count
from django.db.models.functions import Lower
from rest_framework import serializers, status, viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from core.permissions import APIKeyTierPermission, IsAdmin

from .models import RoleLabel
from .serializers import RoleLabelSerializer
from .services import ensure_role_labels_enabled, role_label_user_count


class SystemRoleSerializer(serializers.Serializer):
    id = serializers.CharField()
    name = serializers.CharField()
    description = serializers.CharField(allow_blank=True)
    is_system = serializers.BooleanField()
    user_count = serializers.IntegerField(required=False)


SYSTEM_ROLES = [
    {
        'id': 'system:admin',
        'name': 'Admin',
        'description': 'Full administrative access for the organization.',
        'is_system': True,
    },
    {
        'id': 'system:member',
        'name': 'Member',
        'description': 'Standard member access.',
        'is_system': True,
    },
]


class RoleLabelViewSet(viewsets.ModelViewSet):
    """CRUD for custom display role labels (admin-only, organization-scoped)."""

    serializer_class = RoleLabelSerializer
    permission_classes = [IsAuthenticated, IsAdmin, APIKeyTierPermission]
    lookup_field = 'pk'

    def initial(self, request, *args, **kwargs):
        ensure_role_labels_enabled()
        return super().initial(request, *args, **kwargs)

    def get_queryset(self):
        org = self.request.user.organization
        return (
            RoleLabel.objects.filter(organization=org)
            .annotate(_user_count=Count('user_assignments'))
            .order_by(Lower('name'))
        )

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        serializer = self.get_serializer(queryset, many=True)
        from django.contrib.auth import get_user_model

        User = get_user_model()
        org = request.user.organization
        admin_count = User.objects.filter(organization=org, role='admin').count()
        member_count = User.objects.filter(organization=org, role='member').count()

        system_roles = []
        for role in SYSTEM_ROLES:
            entry = dict(role)
            if role['id'] == 'system:admin':
                entry['user_count'] = admin_count
            elif role['id'] == 'system:member':
                entry['user_count'] = member_count
            system_roles.append(entry)

        return Response({
            'system_roles': system_roles,
            'custom_roles': serializer.data,
        })

    def perform_create(self, serializer):
        serializer.save(organization=self.request.user.organization)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        count = role_label_user_count(instance)
        if count:
            return Response(
                {'detail': f'{count} user{"s" if count != 1 else ""} have this role; reassign them first.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return super().destroy(request, *args, **kwargs)
