"""Parametric coverage hooks for every catalogue permission (allowed/denied paths)."""
import pytest

from permissions_rbac.catalogue import (
    ALL_ROLE_GRANT_PERMISSIONS,
    PERMISSION_DEFINITIONS,
    PERM_DATAROOM_CREATE,
    PERM_DATAROOM_EDIT,
    PERM_DATAROOM_SHARE,
    PERM_FILE_DOWNLOAD,
    PERM_FILE_VIEW,
    PERM_SYSTEM_SIGNATURE,
    PERM_SYSTEM_TRASH,
    ROLE_SLUG_ADMIN,
    ROLE_SLUG_MANAGER,
    SCOPED_DATAROOM_PERMISSIONS,
    default_grants_for_role_slug,
)
from permissions_rbac.models import DataroomRole, DataroomRolePermission
from permissions_rbac.seed import ensure_default_roles_for_organization, reset_all_system_roles_for_organization
from permissions_rbac.services import has_perm, has_system_perm


@pytest.mark.django_db
@pytest.mark.parametrize('codename', ALL_ROLE_GRANT_PERMISSIONS)
def test_permission_definition_exists(codename):
    assert codename in PERMISSION_DEFINITIONS


@pytest.mark.django_db
@pytest.mark.parametrize('codename', SCOPED_DATAROOM_PERMISSIONS)
def test_scoped_permission_supports_own_any(codename):
    definition = PERMISSION_DEFINITIONS[codename]
    assert definition.supports_scope is True


@pytest.mark.django_db
def test_admin_role_denies_system_perm_when_stripped(organization, user):
    ensure_default_roles_for_organization(organization)
    limited = DataroomRole.objects.create(
        organization=organization, slug='no-system', name='No System', is_system=False
    )
    DataroomRolePermission.objects.create(role=limited, permission=PERM_FILE_VIEW, scope='')
    user.organization_role = limited
    user.save(update_fields=['organization_role'])
    assert has_system_perm(user, PERM_SYSTEM_TRASH) is False


@pytest.mark.django_db
def test_admin_template_includes_all_system(organization):
    ensure_default_roles_for_organization(organization)
    admin = DataroomRole.objects.get(organization=organization, slug=ROLE_SLUG_ADMIN)
    granted = {g.permission for g in admin.permission_grants.all()}
    for perm in default_grants_for_role_slug(ROLE_SLUG_ADMIN):
        assert perm in granted


@pytest.mark.django_db
def test_manager_template_excludes_system_by_default(organization):
    ensure_default_roles_for_organization(organization)
    mgr = DataroomRole.objects.get(organization=organization, slug=ROLE_SLUG_MANAGER)
    granted = {g.permission for g in mgr.permission_grants.all()}
    assert PERM_SYSTEM_SIGNATURE not in granted
    assert PERM_DATAROOM_CREATE in granted
    assert PERM_DATAROOM_SHARE in granted


@pytest.mark.django_db
def test_ensure_default_roles_keeps_saved_grants(organization):
    ensure_default_roles_for_organization(organization)
    admin = DataroomRole.objects.get(organization=organization, slug=ROLE_SLUG_ADMIN)
    admin.permission_grants.filter(permission=PERM_DATAROOM_CREATE).delete()
    admin.permission_grants.filter(permission=PERM_FILE_VIEW).delete()

    ensure_default_roles_for_organization(organization)

    granted = set(admin.permission_grants.values_list('permission', flat=True))
    assert PERM_DATAROOM_CREATE not in granted
    assert PERM_FILE_VIEW not in granted
    assert PERM_DATAROOM_EDIT in granted


@pytest.mark.django_db
def test_reset_system_roles_restores_share_grant(organization):
    ensure_default_roles_for_organization(organization)
    admin = DataroomRole.objects.get(organization=organization, slug=ROLE_SLUG_ADMIN)
    admin.permission_grants.all().delete()

    reset_all_system_roles_for_organization(organization)

    granted = set(admin.permission_grants.values_list('permission', flat=True))
    assert PERM_DATAROOM_SHARE in granted
    assert PERM_DATAROOM_CREATE in granted


@pytest.mark.django_db
def test_file_view_download_matrix(user, organization, rbac_roles_from_seed, dataroom_with_viewer):
    room, viewer, dd = dataroom_with_viewer
    assert has_perm(viewer, PERM_FILE_VIEW, room, dd, 'document') is True
    assert has_perm(viewer, PERM_FILE_DOWNLOAD, room, dd, 'document') is True


@pytest.fixture
def rbac_roles_from_seed(organization):
    return ensure_default_roles_for_organization(organization)


@pytest.fixture
def dataroom_with_viewer(user, organization, rbac_roles_from_seed):
    from datarooms.models import Dataroom, DataroomCollaborator, DataroomDocument
    from documents.models import Document, DocumentVersion

    limited = DataroomRole.objects.create(
        organization=organization, slug='matrix-view', name='Matrix View', is_system=False
    )
    DataroomRolePermission.objects.bulk_create(
        [
            DataroomRolePermission(role=limited, permission=PERM_FILE_VIEW, scope=''),
            DataroomRolePermission(role=limited, permission=PERM_FILE_DOWNLOAD, scope=''),
        ]
    )
    viewer = user.__class__.objects.create_user(
        username='matrix-viewer@test.com',
        email='matrix-viewer@test.com',
        password='password123',
        organization=organization,
        organization_role=limited,
    )
    room = Dataroom.objects.create(name='Matrix Room', organization=organization, created_by=user)
    DataroomCollaborator.objects.create(dataroom=room, user=viewer, invited_by=user)
    doc = Document.objects.create(
        name='m.pdf', created_by=user, organization=organization, status='ready', file_size=10
    )
    DocumentVersion.objects.create(
        document=doc, version_number=1, is_primary=True, original_storage_key='x', file_size=10
    )
    dd = DataroomDocument.objects.create(dataroom=room, document=doc, name='m.pdf')
    return room, viewer, dd
