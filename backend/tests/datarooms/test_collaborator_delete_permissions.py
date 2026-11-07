"""RBAC default and enforcement for dataroom delete permissions (legacy toggles removed)."""

from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from datarooms.models import Dataroom
from permissions_rbac.catalogue import PERM_DATAROOM_DELETE, PERM_FOLDER_DELETE
from permissions_rbac.models import DataroomRolePermission
from permissions_rbac.services import invalidate_organization_rbac_cache
from permissions_rbac.catalogue import SCOPE_ANY
from django.contrib.auth import get_user_model
from tests.datarooms.rbac_test_helpers import editor_role, make_shared_dataroom

User = get_user_model()


class CollaboratorDeletePermissionsTests(APITestCase):
    def setUp(self):
        self.owner = User.objects.create_user(
            username="owner@example.com",
            email="owner@example.com",
            password="password",
        )
        self.editor = User.objects.create_user(
            username="editor@example.com",
            email="editor@example.com",
            password="password",
        )
        self.other = User.objects.create_user(
            username="other@example.com",
            email="other@example.com",
            password="password",
        )
        self.dataroom, self.owner_dd, self.editor_dd, _ = make_shared_dataroom(
            self.owner,
            self.editor,
            self.other,
        )

    def _remove_content_url(self):
        return reverse('dataroom-remove-content', kwargs={'pk': self.dataroom.pk})

    def test_editor_can_delete_own_document_not_others(self):
        self.client.force_authenticate(user=self.editor)
        response = self.client.post(
            self._remove_content_url(),
            {'dataroom_document_ids': [str(self.editor_dd.pk)]},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(self.editor_dd.__class__.objects.filter(pk=self.editor_dd.pk).exists())

        response = self.client.post(
            self._remove_content_url(),
            {'dataroom_document_ids': [str(self.owner_dd.pk)]},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_editor_cannot_delete_dataroom(self):
        self.client.force_authenticate(user=self.editor)
        response = self.client.delete(
            reverse("dataroom-detail", kwargs={"pk": self.dataroom.pk})
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_owner_can_delete_dataroom(self):
        dr = Dataroom.objects.create(
            name="Owner Delete",
            created_by=self.owner,
            organization=self.owner.organization,
        )
        self.client.force_authenticate(user=self.owner)
        response = self.client.delete(reverse("dataroom-detail", kwargs={"pk": dr.pk}))
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_widening_delete_grant_allows_cross_user_delete(self):
        editor_rbac = editor_role(self.owner.organization)
        DataroomRolePermission.objects.filter(
            role=editor_rbac,
            permission=PERM_FOLDER_DELETE,
        ).update(scope=SCOPE_ANY)
        invalidate_organization_rbac_cache(str(self.owner.organization_id))

        self.client.force_authenticate(user=self.editor)
        response = self.client.post(
            self._remove_content_url(),
            {'dataroom_document_ids': [str(self.owner_dd.pk)]},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
