import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from core.authentication import generate_raw_api_key
from core.models import APIKey
from datarooms.models import Dataroom
from permissions_rbac.catalogue import PERM_DATAROOM_CREATE, PERM_SYSTEM_API_KEYS, PERM_SYSTEM_DOCUMENTS
from permissions_rbac.models import DataroomRole, DataroomRolePermission
from permissions_rbac.seed import ensure_default_roles_for_organization
from permissions_rbac.services import invalidate_organization_rbac_cache


def _grant_member_rbac(user, extra=()):
    ensure_default_roles_for_organization(user.organization)
    role, _ = DataroomRole.objects.get_or_create(
        organization=user.organization,
        slug='api-member',
        defaults={'name': 'API Member', 'is_system': False},
    )
    DataroomRolePermission.objects.filter(role=role).delete()
    perms = {PERM_SYSTEM_API_KEYS: '', PERM_SYSTEM_DOCUMENTS: ''}
    for perm in extra:
        perms[perm] = ''
    DataroomRolePermission.objects.bulk_create(
        [DataroomRolePermission(role=role, permission=p, scope=s) for p, s in perms.items()]
    )
    user.organization_role = role
    user.save(update_fields=['organization_role'])
    invalidate_organization_rbac_cache(str(user.organization_id))


def _create_client_with_api_key(user, tier):
    raw_key, prefix, hashed_key = generate_raw_api_key()
    APIKey.objects.create(
        user=user,
        name=f'{tier} Key',
        prefix=prefix,
        hashed_key=hashed_key,
        tier=tier,
    )
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f'Bearer {raw_key}')
    return client


@pytest.mark.django_db
def test_read_only_api_key_perm_on_datarooms(user):
    _grant_member_rbac(user)
    client = _create_client_with_api_key(user, 'read_only')
    dataroom = Dataroom.objects.create(name='Test Room', created_by=user, organization=user.organization)

    list_resp = client.get(reverse('dataroom-list'))
    assert list_resp.status_code == status.HTTP_200_OK

    create_resp = client.post(reverse('dataroom-list'), {'name': 'New Room'}, format='json')
    assert create_resp.status_code == status.HTTP_403_FORBIDDEN
    assert 'read_only' in str(create_resp.data['detail'])

    delete_resp = client.delete(reverse('dataroom-detail', args=[dataroom.id]))
    assert delete_resp.status_code == status.HTTP_403_FORBIDDEN
    assert 'read_only' in str(delete_resp.data['detail'])


@pytest.mark.django_db
def test_read_write_api_key_perm_on_datarooms(user):
    _grant_member_rbac(user, extra=(PERM_DATAROOM_CREATE,))
    client = _create_client_with_api_key(user, 'read_write')
    dataroom = Dataroom.objects.create(name='Test Room', created_by=user, organization=user.organization)

    create_resp = client.post(reverse('dataroom-list'), {'name': 'New Write Room'}, format='json')
    assert create_resp.status_code == status.HTTP_201_CREATED

    delete_resp = client.delete(reverse('dataroom-detail', args=[dataroom.id]))
    assert delete_resp.status_code == status.HTTP_403_FORBIDDEN
    assert 'read_write' in str(delete_resp.data['detail'])


@pytest.mark.django_db
def test_full_access_api_key_perm_on_datarooms(user):
    _grant_member_rbac(user)
    client = _create_client_with_api_key(user, 'full_access')
    dataroom = Dataroom.objects.create(name='Test Room', created_by=user, organization=user.organization)

    delete_resp = client.delete(reverse('dataroom-detail', args=[dataroom.id]))
    assert delete_resp.status_code == status.HTTP_204_NO_CONTENT
