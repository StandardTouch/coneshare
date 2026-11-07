"""Matrix tests for redesigned RBAC permissions."""
import pytest
from rest_framework import status
from rest_framework.test import APIClient

from core.models import User
from datarooms.models import Dataroom, DataroomCollaborator, DataroomDocument
from documents.models import Document, DocumentVersion
from permissions_rbac.catalogue import (
    ALL_ROLE_GRANT_PERMISSIONS,
    PERM_DATAROOM_SETTINGS_TAB,
    PERM_FILE_VIEW,
    PERM_SYSTEM_SIGNATURE,
    PERM_SYSTEM_TRASH,
    ROLE_SLUG_ADMIN,
    ROLE_SLUG_MANAGER,
    SCOPED_DATAROOM_PERMISSIONS,
    default_grants_for_role_slug,
)
from permissions_rbac.models import DataroomRole, DataroomRolePermission
from permissions_rbac.safety import is_primary_org_admin, user_has_full_access
from permissions_rbac.seed import ensure_default_roles_for_organization
from permissions_rbac.services import has_perm, has_system_perm, resolve_organization_role


def _doc(name, creator, organization):
    doc = Document.objects.create(
        name=name,
        created_by=creator,
        organization=organization,
        status='ready',
        file_size=128,
    )
    DocumentVersion.objects.create(
        document=doc,
        version_number=1,
        is_primary=True,
        original_storage_key=f'org/{name}',
        file_size=128,
    )
    return doc


@pytest.fixture
def rbac_roles(organization):
    return ensure_default_roles_for_organization(organization)


@pytest.fixture
def limited_role(organization, rbac_roles):
    role = DataroomRole.objects.create(
        organization=organization,
        slug='limited',
        name='Limited',
        is_system=False,
    )
    DataroomRolePermission.objects.bulk_create(
        [
            DataroomRolePermission(role=role, permission=PERM_FILE_VIEW, scope=''),
            DataroomRolePermission(
                role=role, permission='file_download', scope=''
            ),
        ]
    )
    return role


@pytest.mark.django_db
class TestAdminDefaultsAndSafety:
    def test_only_admin_manager_system_roles(self, organization, rbac_roles):
        slugs = set(
            DataroomRole.objects.filter(organization=organization, is_system=True).values_list('slug', flat=True)
        )
        assert slugs == {ROLE_SLUG_ADMIN, ROLE_SLUG_MANAGER}

    def test_admin_role_has_full_catalogue(self, organization, rbac_roles):
        admin = DataroomRole.objects.get(organization=organization, slug=ROLE_SLUG_ADMIN)
        grants = {g.permission for g in admin.permission_grants.all()}
        assert grants == set(ALL_ROLE_GRANT_PERMISSIONS)

    def test_primary_admin_safety(self, admin_user):
        assert is_primary_org_admin(admin_user)
        assert user_has_full_access(admin_user)

    def test_manager_lacks_system_perms_by_default(self, organization, rbac_roles, user):
        manager_role = DataroomRole.objects.get(organization=organization, slug=ROLE_SLUG_MANAGER)
        user.organization_role = manager_role
        user.save(update_fields=['organization_role'])
        assert has_system_perm(user, PERM_SYSTEM_SIGNATURE) is False
        assert has_system_perm(user, PERM_SYSTEM_TRASH) is False


@pytest.mark.django_db
class TestDataroomSettingsEnforcement:
    def test_settings_patch_403_without_tab_perm(self, user, organization, rbac_roles, limited_role):
        member = User.objects.create_user(
            username='limited@test.com',
            email='limited@test.com',
            password='password123',
            organization=organization,
            organization_role=limited_role,
        )
        room = Dataroom.objects.create(name='Room', organization=organization, created_by=user)
        DataroomCollaborator.objects.create(dataroom=room, user=member, invited_by=user)
        client = APIClient()
        client.force_authenticate(user=member)
        resp = client.patch(f'/api/v1/datarooms/{room.id}/', {'enable_qna': False}, format='json')
        assert resp.status_code == status.HTTP_403_FORBIDDEN

    def test_settings_allowed_with_grants(self, user, organization, rbac_roles):
        manager = User.objects.create_user(
            username='mgr2@test.com',
            email='mgr2@test.com',
            password='password123',
            organization=organization,
            organization_role=DataroomRole.objects.get(organization=organization, slug=ROLE_SLUG_MANAGER),
        )
        room = Dataroom.objects.create(name='Room2', organization=organization, created_by=user)
        DataroomCollaborator.objects.create(dataroom=room, user=manager, invited_by=user)
        # Grant settings tab + edit on manager role
        role = manager.organization_role
        for perm in (PERM_DATAROOM_SETTINGS_TAB, 'dataroom_edit'):
            DataroomRolePermission.objects.get_or_create(role=role, permission=perm, defaults={'scope': ''})
        client = APIClient()
        client.force_authenticate(user=manager)
        resp = client.patch(f'/api/v1/datarooms/{room.id}/', {'enable_qna': False}, format='json')
        assert resp.status_code == status.HTTP_200_OK


@pytest.mark.django_db
class TestOrgRoleAppliesInDataroom:
    def test_collaborator_uses_organization_role_not_per_dataroom_role(
        self, user, organization, rbac_roles, limited_role
    ):
        member = User.objects.create_user(
            username='collab@test.com',
            email='collab@test.com',
            password='password123',
            organization=organization,
            organization_role=limited_role,
        )
        room = Dataroom.objects.create(name='R', organization=organization, created_by=user)
        DataroomCollaborator.objects.create(dataroom=room, user=member, invited_by=user, dataroom_role=None)
        doc = _doc('a.pdf', user, organization)
        dd = DataroomDocument.objects.create(dataroom=room, document=doc, name=doc.name)
        assert has_perm(member, PERM_FILE_VIEW, room, dd, 'document') is True
        assert has_perm(member, 'rename', room, dd, 'document') is False


@pytest.mark.django_db
class TestCatalogueDefaults:
    @pytest.mark.parametrize('slug', [ROLE_SLUG_ADMIN, ROLE_SLUG_MANAGER])
    def test_default_grants_valid(self, slug):
        grants = default_grants_for_role_slug(slug)
        for perm in grants:
            assert perm in ALL_ROLE_GRANT_PERMISSIONS
        for perm, scope in grants.items():
            if perm in SCOPED_DATAROOM_PERMISSIONS:
                assert scope in ('any', 'own', None)


@pytest.mark.django_db
class TestAdminUsersList:
    def test_admin_users_list_ok(self, admin_user):
        client = APIClient()
        client.force_authenticate(user=admin_user)
        resp = client.get('/api/v1/admin/users/')
        assert resp.status_code == status.HTTP_200_OK
