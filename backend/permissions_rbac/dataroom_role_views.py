from rest_framework.response import Response
from rest_framework.views import APIView

from datarooms.models import Dataroom
from datarooms.utils import is_dataroom_collaborator_or_above, is_dataroom_owner_or_admin
from permissions_rbac.models import DataroomRole
from permissions_rbac.seed import ensure_default_roles_for_organization
from permissions_rbac.serializers import DataroomRoleSerializer


class DataroomRoleOptionsView(APIView):
    """Lists assignable dataroom roles for collaborator management."""

    def get(self, request, dataroom_id):
        dataroom = Dataroom.objects.filter(id=dataroom_id, organization=request.user.organization).first()
        if not dataroom:
            return Response(status=404)
        if not is_dataroom_owner_or_admin(request.user, dataroom) and not is_dataroom_collaborator_or_above(
            request.user, dataroom
        ):
            return Response(status=403)
        ensure_default_roles_for_organization(request.user.organization)
        roles = DataroomRole.objects.filter(organization=request.user.organization).order_by('name')
        return Response(DataroomRoleSerializer(roles, many=True, context={'request': request}).data)
