"""Folder access rules were removed in the RBAC redesign."""
from rest_framework import status, viewsets
from rest_framework.response import Response


class DataroomFolderRuleViewSet(viewsets.ViewSet):
    def list(self, request, *args, **kwargs):
        return Response(status=status.HTTP_410_GONE)

    def create(self, request, *args, **kwargs):
        return Response({'detail': 'Folder access rules are no longer supported.'}, status=status.HTTP_410_GONE)
