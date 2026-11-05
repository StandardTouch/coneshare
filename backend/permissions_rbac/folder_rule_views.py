"""Folder-level access rules (owner/manager configuration)."""
from rest_framework import status, viewsets
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.response import Response

from datarooms.models import DataroomFolder
from datarooms.utils import is_dataroom_owner_or_admin
from permissions_rbac.audit import log_permission_change
from permissions_rbac.models import DataroomFolderRoleRule, PermissionAuditLog
from permissions_rbac.serializers import DataroomFolderRoleRuleSerializer
from permissions_rbac.services import (
    has_perm,
    invalidate_folder_rule_cache,
    invalidate_organization_rbac_cache,
)
from permissions_rbac.catalogue import PERM_EDIT_DATAROOM_SETTINGS


class DataroomFolderRuleViewSet(viewsets.ViewSet):
    """Manage folder rules for a dataroom folder (authenticated owner/manager)."""

    def list(self, request):
        folder_id = request.query_params.get('folder_id')
        if not folder_id:
            raise ValidationError({'folder_id': 'Required.'})
        folder = DataroomFolder.objects.select_related('dataroom').filter(id=folder_id).first()
        if not folder:
            return Response(status=status.HTTP_404_NOT_FOUND)
        dataroom = folder.dataroom
        if not is_dataroom_owner_or_admin(request.user, dataroom) and not has_perm(
            request.user, PERM_EDIT_DATAROOM_SETTINGS, dataroom
        ):
            raise PermissionDenied()
        rules = DataroomFolderRoleRule.objects.filter(dataroom_folder=folder).select_related(
            'dataroom_role'
        )
        return Response(DataroomFolderRoleRuleSerializer(rules, many=True).data)

    def create(self, request):
        serializer = DataroomFolderRoleRuleSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        folder = serializer.validated_data['dataroom_folder']
        dataroom = folder.dataroom
        if not is_dataroom_owner_or_admin(request.user, dataroom) and not has_perm(
            request.user, PERM_EDIT_DATAROOM_SETTINGS, dataroom
        ):
            raise PermissionDenied()
        rule_obj, _ = DataroomFolderRoleRule.objects.update_or_create(
            dataroom_folder=folder,
            dataroom_role=serializer.validated_data['dataroom_role'],
            defaults={'rule': serializer.validated_data['rule']},
        )
        invalidate_folder_rule_cache(rule_obj.dataroom_role)
        invalidate_organization_rbac_cache(str(dataroom.organization_id))
        log_permission_change(
            request.user,
            PermissionAuditLog.TARGET_FOLDER_RULE,
            str(rule_obj.id),
            f'Set folder rule {rule_obj.rule} for role {rule_obj.dataroom_role.name}',
            {'folder_id': str(folder.id), 'role_id': str(rule_obj.dataroom_role_id)},
        )
        return Response(DataroomFolderRoleRuleSerializer(rule_obj).data, status=status.HTTP_201_CREATED)
