import { describe, expect, it } from 'vitest';
import { buildRolePayload, displayRoleName, roleSelectionFromUser } from '../../lib/adminOrgRoles';

describe('adminOrgRoles', () => {
  const t = (key) => key;

  it('maps admin user to admin selection', () => {
    expect(roleSelectionFromUser({ role: 'admin' })).toBe('admin');
  });

  it('maps organization role id', () => {
    expect(roleSelectionFromUser({ role: 'member', organization_role: { id: 'r1' } })).toBe('r1');
  });

  it('builds organization role payload', () => {
    expect(buildRolePayload('admin')).toEqual({
      role: 'admin',
      organization_role_id: null,
      role_label_id: null,
    });
    expect(buildRolePayload('r1')).toEqual({
      role: 'member',
      organization_role_id: 'r1',
      role_label_id: null,
    });
  });

  it('displays organization role name', () => {
    expect(displayRoleName({ role: 'member', organization_role: { name: 'Viewer' } }, t)).toBe('Viewer');
    expect(displayRoleName({ role: 'admin' }, t)).toBe('admin.roleAdmin');
  });
});
