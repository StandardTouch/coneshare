/**
 * Build API payload and display strings for admin role + optional custom label.
 */

export function roleSelectionFromUser(user) {
  if (!user) return 'member';
  if (user.role === 'admin') return 'admin';
  if (user.role_label?.id) return user.role_label.id;
  return 'member';
}

export function buildRolePayload(roleSelection) {
  if (roleSelection === 'admin') {
    return { role: 'admin', role_label_id: null };
  }
  if (roleSelection === 'member') {
    return { role: 'member', role_label_id: null };
  }
  return { role: 'member', role_label_id: roleSelection };
}

export function displayRoleName(user, t) {
  if (user?.role_label?.name) {
    return user.role_label.name;
  }
  if (user?.role === 'admin') {
    return t('admin.roleAdmin');
  }
  return t('admin.roleMember');
}
