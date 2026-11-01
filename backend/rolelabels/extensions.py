from core.admin_views import AdminUserViewSet
from core.services import get_dynamic_setting


_original_get_queryset = AdminUserViewSet.get_queryset


def get_queryset_with_role_labels(self):
    queryset = _original_get_queryset(self)
    if get_dynamic_setting('ROLE_LABELS_ENABLED'):
        return queryset.select_related('role_label_assignment__role_label')
    return queryset


AdminUserViewSet.get_queryset = get_queryset_with_role_labels
