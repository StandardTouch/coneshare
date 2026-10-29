import pytest
from esign.services import calculate_document_hash, generate_otp_code


@pytest.mark.django_db
class TestServices:
    """Test esign service functions"""
    
    def test_generate_otp_code(self):
        """OTP code is 6 digits"""
        code = generate_otp_code()
        assert len(code) == 6
        assert code.isdigit()
        
        # Generate multiple codes to check uniqueness
        codes = [generate_otp_code() for _ in range(10)]
        # At least some should be different
        assert len(set(codes)) > 1
    
    def test_calculate_document_hash(self):
        """Document hash is SHA-256"""
        pdf_bytes = b"test pdf content"
        hash_result = calculate_document_hash(pdf_bytes)
        
        assert hash_result.startswith('sha256:')
        assert len(hash_result) == 71  # 'sha256:' + 64 hex chars
