import pytest
from django.conf import settings
from rest_framework.settings import api_settings
from rest_framework.views import APIView

pytest_plugins = ["esign.tests.test_views"]


def pytest_configure(config):
    config.addinivalue_line(
        "markers",
        "postgres: requires PostgreSQL (enforces varchar length limits)",
    )
    config.addinivalue_line(
        "markers",
        "esign_rbac_enforcement: run real signature RBAC checks (no autouse bypass)",
    )


@pytest.fixture
def require_postgres(db):
    from django.db import connection

    if connection.vendor != "postgresql":
        pytest.skip("PostgreSQL-only test")


@pytest.fixture(autouse=True)
def disable_redis_cache(settings):
    """Use in-memory cache when pytest runs outside Docker."""
    settings.CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        }
    }


@pytest.fixture(autouse=True)
def _allow_signature_unless_rbac_toggle_tests(request, monkeypatch):
    """Integration tests expect signature access unless explicitly testing RBAC denial."""
    if request.node.get_closest_marker("esign_rbac_enforcement"):
        return
    monkeypatch.setattr(
        "featuregates.services.ensure_signature_enabled_for_user",
        lambda user: None,
    )
    monkeypatch.setattr("esign.views.check_esign_enabled", lambda user: None)
    try:
        import esign.pdf_views as esign_pdf_views

        if hasattr(esign_pdf_views, "check_esign_enabled"):
            monkeypatch.setattr(esign_pdf_views, "check_esign_enabled", lambda user: None)
    except ImportError:
        pass


@pytest.fixture
def enable_esign():
    """Backward-compatible no-op (signature access handled by autouse bypass)."""
    yield


@pytest.fixture(autouse=True)
def disable_drf_rate_limiting(settings):
    """Disable DRF throttling during esign pytest runs."""
    rf_settings = settings.REST_FRAMEWORK.copy()
    rf_settings["DEFAULT_THROTTLE_CLASSES"] = []
    rf_rates = rf_settings.get("DEFAULT_THROTTLE_RATES", {}).copy()
    rf_rates["anon"] = None
    rf_rates["user"] = None
    rf_settings["DEFAULT_THROTTLE_RATES"] = rf_rates
    settings.REST_FRAMEWORK = rf_settings

    api_settings.DEFAULT_THROTTLE_CLASSES = []
    api_settings.DEFAULT_THROTTLE_RATES["anon"] = None
    api_settings.DEFAULT_THROTTLE_RATES["user"] = None
    APIView.throttle_classes = []
