import pytest
from django.conf import settings
from rest_framework.settings import api_settings
from rest_framework.views import APIView

pytest_plugins = ["esign.tests.test_views"]


@pytest.fixture(autouse=True)
def disable_redis_cache(settings):
    """Use in-memory cache when pytest runs outside Docker."""
    settings.CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        }
    }


@pytest.fixture
def enable_esign(db, monkeypatch):
    monkeypatch.setattr(settings, "ESIGN_ENABLED", True)
    yield
    monkeypatch.setattr(settings, "ESIGN_ENABLED", False)


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
