from core.admin_views import AdminUserViewSet
from core.db_schema import user_has_organization_role_column
_original_get_queryset = AdminUserViewSet.get_queryset


def get_queryset_with_role_labels(self):
    queryset = _original_get_queryset(self)
    if user_has_organization_role_column():
        return queryset.select_related('organization_role')
    return queryset.select_related('role_label_assignment__role_label')


AdminUserViewSet.get_queryset = get_queryset_with_role_labels
