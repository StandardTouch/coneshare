from permissions_rbac.models import PermissionAuditLog


def log_permission_change(user, target_type, target_id, summary, details=None):
    if user is None or not getattr(user, 'organization_id', None):
        return
    PermissionAuditLog.objects.create(
        organization_id=user.organization_id,
        actor=user,
        target_type=target_type,
        target_id=target_id or '',
        summary=summary,
        details=details or {},
    )
