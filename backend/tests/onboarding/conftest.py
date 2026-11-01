import pytest


@pytest.fixture(autouse=True)
def local_cache_for_onboarding_tests(settings):
    settings.CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        }
    }
