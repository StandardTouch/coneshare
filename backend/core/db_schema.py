"""Helpers for optional / not-yet-migrated schema columns."""
from functools import lru_cache

from django.contrib.auth import get_user_model
from django.db import connection


@lru_cache(maxsize=1)
def user_has_organization_role_column() -> bool:
    """True when core_user.organization_role_id exists (post core.0009 migration)."""
    user = get_user_model()
    table = user._meta.db_table
    try:
        with connection.cursor() as cursor:
            description = connection.introspection.get_table_description(cursor, table)
    except Exception:
        return False
    return any(col.name == 'organization_role_id' for col in description)
