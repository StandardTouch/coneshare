import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from datarooms.models import Dataroom, DataroomCollaborator, DataroomDocument, DataroomFolder
from documents.models import Document, DocumentVersion
from permissions_rbac.catalogue import PERM_FILE_VIEW, SCOPE_OWN
from permissions_rbac.models import DataroomRole, DataroomRolePermission
from permissions_rbac.services import invalidate_organization_rbac_cache

User = get_user_model()


def _ready_doc(name, creator, organization):
    document = Document.objects.create(
        name=name,
        created_by=creator,
        organization=organization,
        status='ready',
        file_size=100,
        type='pdf',
    )
    DocumentVersion.objects.create(
        document=document,
        version_number=1,
        is_primary=True,
        original_storage_key=f'org/{name}',
        file_size=100,
        content_type='application/pdf',
        type='pdf',
    )
    return document


@pytest.mark.django_db
def test_dataroom_list_search_matches_name(api_client, user, organization):
    Dataroom.objects.create(name='Alpha Clinic', organization=organization, created_by=user)
    Dataroom.objects.create(name='Beta Archive', organization=organization, created_by=user)

    response = api_client.get('/api/v1/datarooms/', {'search': 'alpha'})

    assert response.status_code == 200
    names = [room['name'] for room in response.data]
    assert names == ['Alpha Clinic']


@pytest.mark.django_db
def test_content_search_returns_nested_file_and_its_folder(api_client, user, organization):
    room = Dataroom.objects.create(name='Clinic Room', organization=organization, created_by=user)
    contracts = DataroomFolder.objects.create(dataroom=room, name='Contracts', created_by=user)
    legal = DataroomFolder.objects.create(
        dataroom=room, name='Legal', parent=contracts, created_by=user
    )
    DataroomFolder.objects.create(dataroom=room, name='Archive', created_by=user)
    DataroomDocument.objects.create(
        dataroom=room,
        document=_ready_doc('Budget.pdf', user, organization),
        folder=legal,
        name='Budget.pdf',
    )
    DataroomDocument.objects.create(
        dataroom=room,
        document=_ready_doc('Welcome.pdf', user, organization),
        name='Welcome.pdf',
    )

    response = api_client.get(f'/api/v1/datarooms/{room.id}/search/', {'q': 'budget'})

    assert response.status_code == 200
    items = response.data['items']
    by_name = {item['name']: item for item in items}
    assert set(by_name) == {'Legal', 'Budget.pdf'}
    assert by_name['Legal']['type'] == 'folder'
    assert by_name['Legal']['location'] == 'Contracts'
    assert by_name['Budget.pdf']['type'] == 'document'
    assert by_name['Budget.pdf']['location'] == 'Contracts / Legal'


@pytest.mark.django_db
def test_content_search_own_scope_hides_other_peoples_files(organization, user, user2):
    room = Dataroom.objects.create(name='Clinic Room', organization=organization, created_by=user)
    legal = DataroomFolder.objects.create(dataroom=room, name='Legal', created_by=user)
    DataroomDocument.objects.create(
        dataroom=room,
        document=_ready_doc('Owner Budget.pdf', user, organization),
        folder=legal,
        name='Owner Budget.pdf',
    )
    DataroomDocument.objects.create(
        dataroom=room,
        document=_ready_doc('My Budget.pdf', user2, organization),
        folder=legal,
        name='My Budget.pdf',
    )
    role = DataroomRole.objects.create(
        organization=organization,
        slug='search-own-viewer',
        name='Search Own Viewer',
        is_system=False,
    )
    DataroomRolePermission.objects.create(role=role, permission=PERM_FILE_VIEW, scope=SCOPE_OWN)
    invalidate_organization_rbac_cache(str(organization.id))
    user2.organization_role = role
    user2.save(update_fields=['organization_role'])
    DataroomCollaborator.objects.create(dataroom=room, user=user2, dataroom_role=role, invited_by=user)

    client = APIClient()
    client.force_authenticate(user=user2)
    response = client.get(f'/api/v1/datarooms/{room.id}/search/', {'q': 'budget'})

    assert response.status_code == 200
    names = {item['name'] for item in response.data['items']}
    assert names == {'Legal', 'My Budget.pdf'}
