"""RBAC enforcement across dataroom access paths."""
import pytest
from unittest.mock import patch
from rest_framework import status
from rest_framework.test import APIClient

from core.models import User
from datarooms.models import Dataroom, DataroomCollaborator, DataroomDocument, DataroomFolder
from documents.models import Document, DocumentVersion
from permissions_rbac.catalogue import (
    ROLE_SLUG_CONTRIBUTOR,
    ROLE_SLUG_EDITOR,
    ROLE_SLUG_MANAGER,
    ROLE_SLUG_VIEWER,
)
from permissions_rbac.services import has_perm
from permissions_rbac.models import DataroomFolderRoleRule, DataroomRole
from permissions_rbac.seed import ensure_default_roles_for_organization


def _doc(name, creator, organization):
    doc = Document.objects.create(
        name=name,
        created_by=creator,
        organization=organization,
        status='ready',
        file_size=256,
    )
    DocumentVersion.objects.create(
        document=doc,
        version_number=1,
        is_primary=True,
        original_storage_key=f'org/{name}',
        file_size=256,
    )
    return doc


@pytest.fixture
def rbac_roles(organization):
    return ensure_default_roles_for_organization(organization)


@pytest.fixture
def rbac_room(user, organization, rbac_roles):
    return Dataroom.objects.create(name='RBAC Enforcement Room', organization=organization, created_by=user)


def _assign(room, target_user, slug, invited_by):
    role = DataroomRole.objects.get(organization=room.organization, slug=slug)
    DataroomCollaborator.objects.create(
        dataroom=room,
        user=target_user,
        invited_by=invited_by,
        dataroom_role=role,
    )


@pytest.fixture
def viewer_user(db, organization):
    return User.objects.create_user(
        username='rbac_viewer@test.com',
        email='rbac_viewer@test.com',
        password='password123',
        organization=organization,
    )


@pytest.fixture
def contributor_user(db, organization):
    return User.objects.create_user(
        username='rbac_contrib@test.com',
        email='rbac_contrib@test.com',
        password='password123',
        organization=organization,
    )


@pytest.mark.django_db
class TestLegacyEditorParity:
    @patch('datarooms.collaborator_delete_permissions.get_dynamic_setting', return_value=True)
    @patch('datarooms.dataroom_create_policy.get_dynamic_setting', return_value=True)
    def test_editor_role_matches_legacy_collaborator_modify_rules(
        self, _own, _create, user, viewer_user, organization, rbac_room, rbac_roles
    ):
        editor = User.objects.create_user(
            username='legacy_editor@test.com',
            email='legacy_editor@test.com',
            password='password123',
            organization=organization,
        )
        _assign(rbac_room, editor, ROLE_SLUG_EDITOR, user)
        owner_doc = _doc('legacy_owner.pdf', user, organization)
        own_doc = _doc('legacy_own.pdf', editor, organization)
        dd_owner = DataroomDocument.objects.create(dataroom=rbac_room, document=owner_doc, name=owner_doc.name)
        dd_own = DataroomDocument.objects.create(dataroom=rbac_room, document=own_doc, name=own_doc.name)
        client = APIClient()
        client.force_authenticate(user=editor)
        blocked = client.patch(f'/api/v1/dataroom-documents/{dd_owner.id}/', {'name': 'x.pdf'}, format='json')
        assert blocked.status_code == status.HTTP_403_FORBIDDEN
        allowed = client.patch(f'/api/v1/dataroom-documents/{dd_own.id}/', {'name': 'mine.pdf'}, format='json')
        assert allowed.status_code == status.HTTP_200_OK


@pytest.mark.django_db
class TestRoleActionMatrix:
    def test_viewer_cannot_upload(self, user, viewer_user, organization, rbac_room, rbac_roles):
        _assign(rbac_room, viewer_user, ROLE_SLUG_VIEWER, user)
        client = APIClient()
        client.force_authenticate(user=viewer_user)
        resp = client.post(
            f'/api/v1/datarooms/{rbac_room.id}/uploads/request/',
            {'file_name': 'x.pdf', 'file_size': 100, 'content_type': 'application/pdf'},
            format='json',
        )
        assert resp.status_code == status.HTTP_403_FORBIDDEN

    def test_manager_can_upload_to_root(self, user, organization, rbac_room, rbac_roles):
        manager = User.objects.create_user(
            username='rbac_mgr@test.com',
            email='rbac_mgr@test.com',
            password='password123',
            organization=organization,
        )
        _assign(rbac_room, manager, ROLE_SLUG_MANAGER, user)
        client = APIClient()
        client.force_authenticate(user=manager)
        with patch('documents.fileserver.fileserver_client.generate_upload_url', return_value='http://upload'):
            resp = client.post(
                f'/api/v1/datarooms/{rbac_room.id}/uploads/request/',
                {'file_name': 'x.pdf', 'file_size': 100, 'content_type': 'application/pdf'},
                format='json',
            )
        assert resp.status_code == status.HTTP_200_OK


@pytest.mark.django_db
class TestHiddenFolderPaths:
    @pytest.fixture
    def hidden_setup(self, user, viewer_user, organization, rbac_room, rbac_roles):
        _assign(rbac_room, viewer_user, ROLE_SLUG_VIEWER, user)
        viewer_role = DataroomRole.objects.get(organization=organization, slug=ROLE_SLUG_VIEWER)
        visible = DataroomFolder.objects.create(dataroom=rbac_room, name='Visible', created_by=user)
        hidden = DataroomFolder.objects.create(dataroom=rbac_room, name='Hidden', created_by=user)
        secret_doc = _doc('secret.pdf', user, organization)
        dd = DataroomDocument.objects.create(
            dataroom=rbac_room, document=secret_doc, name=secret_doc.name, folder=hidden
        )
        DataroomFolderRoleRule.objects.create(
            dataroom_folder=hidden,
            dataroom_role=viewer_role,
            rule=DataroomFolderRoleRule.RULE_HIDDEN,
        )
        return {'visible': visible, 'hidden': hidden, 'dd': dd, 'viewer': viewer_user}

    def test_retrieve_hidden_folder_404(self, hidden_setup):
        client = APIClient()
        client.force_authenticate(user=hidden_setup['viewer'])
        resp = client.get(f'/api/v1/dataroom-folders/{hidden_setup["hidden"].id}/')
        assert resp.status_code == status.HTTP_404_NOT_FOUND

    def test_retrieve_hidden_document_404(self, hidden_setup):
        client = APIClient()
        client.force_authenticate(user=hidden_setup['viewer'])
        resp = client.get(f'/api/v1/dataroom-documents/{hidden_setup["dd"].id}/')
        assert resp.status_code == status.HTTP_404_NOT_FOUND

    def test_document_download_404(self, hidden_setup):
        client = APIClient()
        client.force_authenticate(user=hidden_setup['viewer'])
        resp = client.get(f'/api/v1/documents/{hidden_setup["dd"].document_id}/download/')
        assert resp.status_code in (status.HTTP_404_NOT_FOUND, status.HTTP_403_FORBIDDEN)

    def test_document_preview_404(self, hidden_setup):
        client = APIClient()
        client.force_authenticate(user=hidden_setup['viewer'])
        resp = client.get(f'/api/v1/documents/{hidden_setup["dd"].document_id}/preview-data/')
        assert resp.status_code in (status.HTTP_404_NOT_FOUND, status.HTTP_403_FORBIDDEN)

    def test_move_into_hidden_folder_forbidden(self, hidden_setup, user, organization, rbac_room, rbac_roles):
        contributor = User.objects.create_user(
            username='move_contrib@test.com',
            email='move_contrib@test.com',
            password='password123',
            organization=organization,
        )
        _assign(rbac_room, contributor, ROLE_SLUG_CONTRIBUTOR, user)
        own_doc = _doc('move_me.pdf', contributor, organization)
        dd = DataroomDocument.objects.create(
            dataroom=rbac_room, document=own_doc, name=own_doc.name, folder=hidden_setup['visible']
        )
        client = APIClient()
        client.force_authenticate(user=contributor)
        resp = client.post(
            f'/api/v1/datarooms/{rbac_room.id}/move-content/',
            {
                'dataroom_document_ids': [str(dd.id)],
                'destination_folder_id': str(hidden_setup['hidden'].id),
            },
            format='json',
        )
        assert resp.status_code == status.HTTP_403_FORBIDDEN

    def test_dataroom_detail_items_omit_hidden(self, hidden_setup, rbac_room):
        client = APIClient()
        client.force_authenticate(user=hidden_setup['viewer'])
        resp = client.get(f'/api/v1/datarooms/{rbac_room.id}/?content=full')
        assert resp.status_code == status.HTTP_200_OK
        ids = {item['id'] for item in resp.data['items']}
        assert str(hidden_setup['hidden'].id) not in ids
        assert str(hidden_setup['dd'].id) not in ids

    def test_visible_folder_tree_omits_hidden_children(self, hidden_setup):
        client = APIClient()
        client.force_authenticate(user=hidden_setup['viewer'])
        resp = client.get(f'/api/v1/dataroom-folders/{hidden_setup["visible"].id}/')
        assert resp.status_code == status.HTTP_200_OK
        sub_ids = {f['id'] for f in resp.data.get('sub_folders', [])}
        doc_ids = {d['id'] for d in resp.data.get('documents', [])}
        assert str(hidden_setup['hidden'].id) not in sub_ids
        assert str(hidden_setup['dd'].id) not in doc_ids

    def test_star_hidden_document_404(self, hidden_setup):
        client = APIClient()
        client.force_authenticate(user=hidden_setup['viewer'])
        resp = client.patch(
            f'/api/v1/dataroom-documents/{hidden_setup["dd"].id}/',
            {'is_starred': True},
            format='json',
        )
        assert resp.status_code == status.HTTP_404_NOT_FOUND

    def test_add_content_to_hidden_folder_forbidden(self, hidden_setup, user, organization, rbac_room, rbac_roles):
        own_doc = _doc('add_me.pdf', hidden_setup['viewer'], organization)
        client = APIClient()
        client.force_authenticate(user=hidden_setup['viewer'])
        resp = client.post(
            f'/api/v1/datarooms/{rbac_room.id}/add-content/',
            {
                'document_ids': [str(own_doc.id)],
                'destination_folder_id': str(hidden_setup['hidden'].id),
            },
            format='json',
        )
        assert resp.status_code in (status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND)

    def test_remove_hidden_document_forbidden(self, hidden_setup, rbac_room):
        client = APIClient()
        client.force_authenticate(user=hidden_setup['viewer'])
        resp = client.post(
            f'/api/v1/datarooms/{rbac_room.id}/remove-content/',
            {'dataroom_document_ids': [str(hidden_setup['dd'].id)]},
            format='json',
        )
        assert resp.status_code in (status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND)


@pytest.mark.django_db
class TestViewOnlyFolder:
    def test_view_only_blocks_rename(self, user, contributor_user, organization, rbac_room, rbac_roles):
        _assign(rbac_room, contributor_user, ROLE_SLUG_CONTRIBUTOR, user)
        role = DataroomRole.objects.get(organization=organization, slug=ROLE_SLUG_CONTRIBUTOR)
        folder = DataroomFolder.objects.create(dataroom=rbac_room, name='ReadOnly', created_by=user)
        own_doc = _doc('ro.pdf', contributor_user, organization)
        dd = DataroomDocument.objects.create(
            dataroom=rbac_room, document=own_doc, name=own_doc.name, folder=folder
        )
        DataroomFolderRoleRule.objects.create(
            dataroom_folder=folder,
            dataroom_role=role,
            rule=DataroomFolderRoleRule.RULE_VIEW_ONLY,
        )
        client = APIClient()
        client.force_authenticate(user=contributor_user)
        resp = client.patch(f'/api/v1/dataroom-documents/{dd.id}/', {'name': 'nope.pdf'}, format='json')
        assert resp.status_code == status.HTTP_403_FORBIDDEN

    def test_view_only_inherited_in_subfolder(self, user, contributor_user, organization, rbac_room, rbac_roles):
        _assign(rbac_room, contributor_user, ROLE_SLUG_CONTRIBUTOR, user)
        role = DataroomRole.objects.get(organization=organization, slug=ROLE_SLUG_CONTRIBUTOR)
        parent = DataroomFolder.objects.create(dataroom=rbac_room, name='ParentRO', created_by=user)
        child = DataroomFolder.objects.create(
            dataroom=rbac_room, name='Child', parent=parent, created_by=user
        )
        own_doc = _doc('child.pdf', contributor_user, organization)
        dd = DataroomDocument.objects.create(
            dataroom=rbac_room, document=own_doc, name=own_doc.name, folder=child
        )
        DataroomFolderRoleRule.objects.create(
            dataroom_folder=parent,
            dataroom_role=role,
            rule=DataroomFolderRoleRule.RULE_VIEW_ONLY,
        )
        client = APIClient()
        client.force_authenticate(user=contributor_user)
        resp = client.patch(f'/api/v1/dataroom-documents/{dd.id}/', {'name': 'nope.pdf'}, format='json')
        assert resp.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.django_db
class TestRolePermissionMatrix:
    def test_contributor_can_upload(self, user, organization, rbac_room, rbac_roles):
        contributor = User.objects.create_user(
            username='contrib_upload@test.com',
            email='contrib_upload@test.com',
            password='password123',
            organization=organization,
        )
        _assign(rbac_room, contributor, ROLE_SLUG_CONTRIBUTOR, user)
        assert has_perm(contributor, 'upload', rbac_room) is True
        assert has_perm(contributor, 'rename', rbac_room) is False

    def test_editor_can_rename_own_document(self, user, organization, rbac_room, rbac_roles):
        editor = User.objects.create_user(
            username='editor_rename@test.com',
            email='editor_rename@test.com',
            password='password123',
            organization=organization,
        )
        _assign(rbac_room, editor, ROLE_SLUG_EDITOR, user)
        own_doc = _doc('mine.pdf', editor, organization)
        dd = DataroomDocument.objects.create(dataroom=rbac_room, document=own_doc, name=own_doc.name)
        assert has_perm(editor, 'rename', rbac_room, dd, 'document') is True

    def test_viewer_cannot_rename_any_document(self, user, viewer_user, organization, rbac_room, rbac_roles):
        _assign(rbac_room, viewer_user, ROLE_SLUG_VIEWER, user)
        owner_doc = _doc('owner.pdf', user, organization)
        dd = DataroomDocument.objects.create(dataroom=rbac_room, document=owner_doc, name=owner_doc.name)
        assert has_perm(viewer_user, 'rename', rbac_room, dd, 'document') is False

    def test_manager_can_invite_collaborators(self, user, organization, rbac_room, rbac_roles):
        manager = User.objects.create_user(
            username='mgr_invite@test.com',
            email='mgr_invite@test.com',
            password='password123',
            organization=organization,
        )
        _assign(rbac_room, manager, ROLE_SLUG_MANAGER, user)
        assert has_perm(manager, 'invite_collaborators', rbac_room) is True

    def test_editor_cannot_manage_collaborators(self, user, organization, rbac_room, rbac_roles):
        editor = User.objects.create_user(
            username='ed_collab@test.com',
            email='ed_collab@test.com',
            password='password123',
            organization=organization,
        )
        _assign(rbac_room, editor, ROLE_SLUG_EDITOR, user)
        assert has_perm(editor, 'manage_collaborators', rbac_room) is False

    def test_owner_has_full_delete_on_others_content(self, user, organization, rbac_room, rbac_roles):
        other = User.objects.create_user(
            username='other@test.com',
            email='other@test.com',
            password='password123',
            organization=organization,
        )
        doc = _doc('other.pdf', other, organization)
        dd = DataroomDocument.objects.create(dataroom=rbac_room, document=doc, name=doc.name)
        assert has_perm(user, 'delete', rbac_room, dd, 'document') is True
