from django.apps import AppConfig


class FeaturegatesConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'featuregates'
    verbose_name = 'Feature gates'

    def ready(self):
        from featuregates import extensions  # noqa: F401
