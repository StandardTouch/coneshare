import pytest
from django.test import override_settings

from esign.services import get_client_info, record_signer_action
from esign.models import SignerAction


@pytest.mark.django_db
class TestEsignClientIp:
    @override_settings(TRUSTED_PROXIES=['127.0.0.1', '::1', '172.16.0.0/12', '10.0.0.0/8'])
    def test_get_client_info_behind_coolify_proxy(self, rf):
        request = rf.post(
            '/api/v1/esign/sign/token/verify_otp/',
            HTTP_X_FORWARDED_FOR='203.0.113.50, 10.0.2.9',
            HTTP_X_REAL_IP='203.0.113.50',
            REMOTE_ADDR='10.0.2.9',
            HTTP_USER_AGENT='Mozilla/5.0 Test Browser',
        )
        ip_address, user_agent = get_client_info(request)
        assert ip_address == '203.0.113.50'
        assert user_agent.startswith('Mozilla/')

    @override_settings(TRUSTED_PROXIES=['127.0.0.1', '::1', '172.16.0.0/12', '10.0.0.0/8'])
    def test_record_signer_action_stores_real_ip(self, rf, signature_request, signer_user):
        signer = signature_request.signers.get(user=signer_user)
        request = rf.post(
            '/api/v1/esign/sign/x/request_otp/',
            HTTP_X_FORWARDED_FOR='198.51.100.99',
            REMOTE_ADDR='10.0.2.9',
        )
        record_signer_action(signer, 'otp_requested', request)
        action = SignerAction.objects.filter(signer=signer, action='otp_requested').latest('timestamp')
        assert action.ip_address == '198.51.100.99'

    def test_untrusted_client_cannot_spoof_xff(self, rf):
        request = rf.post(
            '/api/v1/esign/sign/x/request_otp/',
            HTTP_X_FORWARDED_FOR='203.0.113.7',
            REMOTE_ADDR='198.51.100.5',
        )
        ip_address, _ = get_client_info(request)
        assert ip_address == '198.51.100.5'
