import { useTranslation } from 'react-i18next';
import { Select } from '../ui/Select';
import { roleSelectionFromUser } from '../../lib/adminOrgRoles';

export function RoleSelect({
  user,
  value,
  onChange,
  orgRoles = [],
  customRoles = [],
  disabled = false,
  className,
  id = 'role',
  name = 'roleSelection',
}) {
  const { t } = useTranslation();
  const selected = value ?? roleSelectionFromUser(user);
  const roles = orgRoles.length ? orgRoles : customRoles;

  return (
    <Select
      id={id}
      name={name}
      value={selected}
      onChange={onChange}
      disabled={disabled}
      className={className}
    >
      <option value="admin">{t('admin.roleAdmin')}</option>
      {roles.map((role) => (
        <option key={role.id} value={role.id}>
          {role.name}
          {role.is_system ? ` (${role.slug})` : ''}
        </option>
      ))}
    </Select>
  );
}
