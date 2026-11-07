"""RBAC defaults for modify/create (replaces legacy AppConfiguration toggle tests)."""

from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from permissions_rbac.catalogue import PERM_DATAROOM_CREATE, PERM_FILE_RENAME, SCOPE_ANY
from permissions_rbac.models import DataroomRole, DataroomRolePermission
from permissions_rbac.services import invalidate_organization_rbac_cache
from django.contrib.auth import get_user_model
from tests.datarooms.rbac_test_helpers import editor_role, make_shared_dataroom

User = get_user_model()


class CollaboratorModifyAndCreateTests(APITestCase):
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
        invalidate_organization_rbac_cache(str(self.owner.organization_id))

    def test_member_cannot_create_dataroom_by_default(self):
        member = User.objects.create_user(
            username="member@example.com",
            email="member@example.com",
            password="password",
            organization=self.owner.organization,
        )
        self.client.force_authenticate(user=member)
        response = self.client.post(
            reverse("dataroom-list"),
            {"name": "Member Room"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_can_create_dataroom_by_default(self):
        admin = User.objects.create_user(
            username="admin@example.com",
            email="admin@example.com",
            password="password",
            role="admin",
            organization=self.owner.organization,
        )
        self.client.force_authenticate(user=admin)
        response = self.client.post(
            reverse("dataroom-list"),
            {"name": "Admin Room"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_granting_member_create_dataroom_allows_create(self):
        from permissions_rbac.seed import ensure_default_roles_for_organization

        ensure_default_roles_for_organization(self.owner.organization)
        custom, _ = DataroomRole.objects.get_or_create(
            organization=self.owner.organization,
            slug='creator',
            defaults={'name': 'Creator', 'is_system': False},
        )
        DataroomRolePermission.objects.update_or_create(
            role=custom,
            permission=PERM_DATAROOM_CREATE,
            defaults={'scope': ''},
        )
        invalidate_organization_rbac_cache(str(self.owner.organization_id))

        member = User.objects.create_user(
            username="member2@example.com",
            email="member2@example.com",
            password="password",
            organization=self.owner.organization,
            organization_role=custom,
        )
        self.client.force_authenticate(user=member)
        response = self.client.post(
            reverse("dataroom-list"),
            {"name": "Granted Room"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_editor_cannot_rename_others_document(self):
        self.client.force_authenticate(user=self.editor)
        response = self.client.patch(
            reverse("dataroomdocument-detail", kwargs={"pk": self.owner_dd.pk}),
            {"name": "Hacked"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_editor_can_rename_own_document(self):
        self.client.force_authenticate(user=self.editor)
        response = self.client.patch(
            reverse("dataroomdocument-detail", kwargs={"pk": self.editor_dd.pk}),
            {"name": "Renamed"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.editor_dd.refresh_from_db()
        self.assertEqual(self.editor_dd.name, "Renamed")

    def test_widening_rename_grant_allows_cross_user_rename(self):
        editor_rbac = editor_role(self.owner.organization)
        DataroomRolePermission.objects.filter(
            role=editor_rbac,
            permission=PERM_FILE_RENAME,
        ).update(scope=SCOPE_ANY)
        invalidate_organization_rbac_cache(str(self.owner.organization_id))

        self.client.force_authenticate(user=self.editor)
        response = self.client.patch(
            reverse("dataroomdocument-detail", kwargs={"pk": self.owner_dd.pk}),
            {"name": "Allowed Now"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
