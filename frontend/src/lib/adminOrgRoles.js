/**
 * Build API payload and display strings for admin user organization RBAC roles.
 */

export function roleSelectionFromUser(user) {
  if (!user) return '';
  if (user.role === 'admin') return 'admin';
  if (user.organization_role?.id) return user.organization_role.id;
  if (user.role_label?.id) return user.role_label.id;
  return '';
}

export function buildRolePayload(roleSelection) {
  if (roleSelection === 'admin') {
    return { role: 'admin', organization_role_id: null, role_label_id: null };
  }
  if (!roleSelection) {
    return { role: 'member', organization_role_id: null, role_label_id: null };
  }
  return { role: 'member', organization_role_id: roleSelection, role_label_id: null };
}

export function displayRoleName(user, t) {
  if (user?.organization_role?.name) {
    return user.organization_role.name;
  }
  if (user?.role_label?.name) {
    return user.role_label.name;
  }
  if (user?.role === 'admin') {
    return t('admin.roleAdmin');
  }
  return t('admin.roleMember');
}
