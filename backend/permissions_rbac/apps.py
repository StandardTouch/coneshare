from django.apps import AppConfig


class PermissionsRbacConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'permissions_rbac'
    verbose_name = 'Permissions & RBAC'

    def ready(self):
        from . import signals  # noqa: F401
