import pytest
from datetime import timedelta
from django.utils import timezone
from rest_framework import status
from django.urls import reverse
from core.models import APIKey
from core.authentication import generate_raw_api_key


@pytest.mark.django_db
def test_create_api_key(admin_api_client, admin_user):
    url = reverse('api-key-list')
    payload = {
        'name': 'Test Integration Key',
        'tier': 'read_write',
        'expires_in_days': 30,
    }
    response = admin_api_client.post(url, payload, format='json')
    assert response.status_code == status.HTTP_201_CREATED
    data = response.data
    assert data['name'] == 'Test Integration Key'
    assert data['tier'] == 'read_write'
    assert 'raw_key' in data
    assert data['raw_key'].startswith('cs_live_')
    assert APIKey.objects.filter(user=admin_user, name='Test Integration Key').exists()


@pytest.mark.django_db
def test_list_api_keys(admin_api_client, admin_user):
    raw_key, prefix, hashed_key = generate_raw_api_key()
    APIKey.objects.create(
        user=admin_user,
        name='My MCP Key',
        prefix=prefix,
        hashed_key=hashed_key,
        tier='read_only',
    )

    url = reverse('api-key-list')
    response = admin_api_client.get(url)
    assert response.status_code == status.HTTP_200_OK
    results = response.data if isinstance(response.data, list) else response.data.get('results', [])
    assert len(results) >= 1
    key_data = [k for k in results if k['name'] == 'My MCP Key'][0]
    assert key_data['prefix'] == prefix
    assert 'raw_key' not in key_data  # raw key should not be exposed in list


@pytest.mark.django_db
def test_api_key_authentication_read_only_tier(public_client, user):
    raw_key, prefix, hashed_key = generate_raw_api_key()
    APIKey.objects.create(
        user=user,
        name='Read Only Agent Key',
        prefix=prefix,
        hashed_key=hashed_key,
        tier='read_only',
    )

    public_client.credentials(HTTP_AUTHORIZATION=f'Bearer {raw_key}')

    # GET on resource endpoints allowed for read_only keys
    response = public_client.get('/api/v1/documents/')
    assert response.status_code == status.HTTP_200_OK

    # API key management requires admin (even for GET)
    url = reverse('api-key-list')
    response = public_client.get(url)
    assert response.status_code == status.HTTP_403_FORBIDDEN

    # POST request blocked by read_only tier -> 403 Forbidden
    response = public_client.post(url, {'name': 'Illegal Key'}, format='json')
    assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.django_db
def test_api_key_authentication_read_write_tier(public_client, user):
    raw_key, prefix, hashed_key = generate_raw_api_key()
    key_obj = APIKey.objects.create(
        user=user,
        name='Read Write Agent Key',
        prefix=prefix,
        hashed_key=hashed_key,
        tier='read_write',
    )

    public_client.credentials(HTTP_AUTHORIZATION=f'Bearer {raw_key}')

    response = public_client.get('/api/v1/documents/')
    assert response.status_code == status.HTTP_200_OK

    url = reverse('api-key-list')
    response = public_client.get(url)
    assert response.status_code == status.HTTP_403_FORBIDDEN

    # DELETE request blocked (admin gate and read_write tier) -> 403 Forbidden
    delete_url = reverse('api-key-detail', kwargs={'pk': key_obj.id})
    response = public_client.delete(delete_url)
    assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.django_db
def test_expired_api_key_returns_401_unauthorized(public_client, user):
    raw_key, prefix, hashed_key = generate_raw_api_key()
    past_expiration = timezone.now() - timedelta(days=1)
    APIKey.objects.create(
        user=user,
        name='Expired Key',
        prefix=prefix,
        hashed_key=hashed_key,
        tier='full_access',
        expires_at=past_expiration,
    )

    public_client.credentials(HTTP_AUTHORIZATION=f'Bearer {raw_key}')
    url = reverse('api-key-list')
    response = public_client.get(url)
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.headers.get('WWW-Authenticate') == 'Bearer realm="api"'


@pytest.mark.django_db
def test_invalid_api_key_returns_401_unauthorized(public_client):
    url = reverse('api-key-list')
    public_client.credentials(HTTP_AUTHORIZATION='Bearer cs_live_nonexistent_key_1234567890')
    response = public_client.get(url)
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.headers.get('WWW-Authenticate') == 'Bearer realm="api"'


@pytest.mark.django_db
def test_invalid_jwt_token_returns_401_unauthorized(public_client):
    url = reverse('api-key-list')
    public_client.credentials(HTTP_AUTHORIZATION='Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.invalidtoken')
    response = public_client.get(url)
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.headers.get('WWW-Authenticate') == 'Bearer realm="api"'


@pytest.mark.django_db
def test_api_key_read_write_cannot_escalate_role(public_client, user):
    raw_key, prefix, hashed_key = generate_raw_api_key()
    APIKey.objects.create(
        user=user,
        name='RW Key',
        prefix=prefix,
        hashed_key=hashed_key,
        tier='read_write',
    )
    public_client.credentials(HTTP_AUTHORIZATION=f'Bearer {raw_key}')
    response = public_client.patch(f'/api/v1/users/{user.id}/', {'role': 'admin'})
    assert response.status_code == status.HTTP_200_OK
    user.refresh_from_db()
    assert user.role == 'member'


@pytest.mark.django_db
def test_api_key_read_write_cannot_mutate_admin_endpoints(public_client, admin_user, user):
    raw_key, prefix, hashed_key = generate_raw_api_key()
    APIKey.objects.create(
        user=admin_user,
        name='Admin RW Key',
        prefix=prefix,
        hashed_key=hashed_key,
        tier='read_write',
    )
    public_client.credentials(HTTP_AUTHORIZATION=f'Bearer {raw_key}')

    # GET is allowed for read_write
    response = public_client.get(f'/api/v1/admin/users/{user.id}/')
    assert response.status_code == status.HTTP_200_OK

    # PATCH /api/v1/admin/users/<id>/ is blocked (requires full_access)
    response = public_client.patch(f'/api/v1/admin/users/{user.id}/', {'name': 'Hacked'}, format='json')
    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert "full_access" in response.data.get('detail', '')

    # POST /api/v1/admin/users/<id>/reset-password/ is blocked
    response = public_client.post(f'/api/v1/admin/users/{user.id}/reset-password/', {'password': 'newpass12345'}, format='json')
    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert "full_access" in response.data.get('detail', '')

    # PATCH /api/v1/admin/settings/ is blocked
    response = public_client.patch('/api/v1/admin/settings/', {'ENABLE_PUBLIC_SIGNUP': True}, format='json')
    assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.django_db
def test_api_key_full_access_can_mutate_admin_endpoints(public_client, admin_user, user):
    raw_key, prefix, hashed_key = generate_raw_api_key()
    APIKey.objects.create(
        user=admin_user,
        name='Admin Full Key',
        prefix=prefix,
        hashed_key=hashed_key,
        tier='full_access',
    )
    public_client.credentials(HTTP_AUTHORIZATION=f'Bearer {raw_key}')
    response = public_client.patch(f'/api/v1/admin/users/{user.id}/', {'name': 'Updated by Full Key'}, format='json')
    assert response.status_code == status.HTTP_200_OK
    user.refresh_from_db()
    assert user.name == 'Updated by Full Key'


@pytest.mark.django_db
def test_api_key_read_write_cannot_mint_full_access_key(public_client, user):
    """An API key with read_write tier cannot create a full_access key."""
    raw_key, prefix, hashed_key = generate_raw_api_key()
    APIKey.objects.create(
        user=user,
        name='RW Key',
        prefix=prefix,
        hashed_key=hashed_key,
        tier='read_write',
    )
    public_client.credentials(HTTP_AUTHORIZATION=f'Bearer {raw_key}')
    url = reverse('api-key-list')
    payload = {
        'name': 'Escalated Full Access Key',
        'tier': 'full_access',
    }
    response = public_client.post(url, payload, format='json')
    assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.django_db
def test_inactive_user_api_key_authentication_denied(public_client, user):
    """Verify that an API key belonging to an inactive user account fails authentication."""
    raw_key, prefix, hashed_key = generate_raw_api_key()
    APIKey.objects.create(
        user=user,
        name='Inactive User Key',
        prefix=prefix,
        hashed_key=hashed_key,
        tier='full_access',
    )
    user.is_active = False
    user.save(update_fields=['is_active'])

    public_client.credentials(HTTP_AUTHORIZATION=f'Bearer {raw_key}')

    # Test API key management endpoint
    response = public_client.get(reverse('api-key-list'))
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert 'inactive' in str(response.data.get('detail', '')).lower()

    # Test resource endpoint
    doc_response = public_client.get('/api/v1/documents/')
    assert doc_response.status_code == status.HTTP_401_UNAUTHORIZED
    assert 'inactive' in str(doc_response.data.get('detail', '')).lower()


