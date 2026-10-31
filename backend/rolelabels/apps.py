from django.apps import AppConfig


class RolelabelsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'rolelabels'
    verbose_name = 'Role Labels'

    def ready(self):
        from rolelabels import extensions  # noqa: F401
