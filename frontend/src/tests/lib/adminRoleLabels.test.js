import { describe, expect, it } from 'vitest';
import { buildRolePayload, displayRoleName, roleSelectionFromUser } from '../../lib/adminRoleLabels';

describe('adminRoleLabels', () => {
  const t = (key) => key;

  it('maps user to role selection', () => {
    expect(roleSelectionFromUser({ role: 'admin' })).toBe('admin');
    expect(roleSelectionFromUser({ role: 'member', role_label: { id: 'lbl-1' } })).toBe('lbl-1');
    expect(roleSelectionFromUser({ role: 'member' })).toBe('member');
  });

  it('builds API payload for custom label', () => {
    expect(buildRolePayload('admin')).toEqual({ role: 'admin', role_label_id: null });
    expect(buildRolePayload('member')).toEqual({ role: 'member', role_label_id: null });
    expect(buildRolePayload('lbl-1')).toEqual({ role: 'member', role_label_id: 'lbl-1' });
  });

  it('displays custom label name when present', () => {
    expect(displayRoleName({ role: 'member', role_label: { name: 'L1-member' } }, t)).toBe('L1-member');
    expect(displayRoleName({ role: 'admin' }, t)).toBe('admin.roleAdmin');
  });
});
