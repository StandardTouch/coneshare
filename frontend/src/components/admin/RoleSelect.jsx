import { useTranslation } from 'react-i18next';
import { Select } from '../ui/Select';
import { roleSelectionFromUser } from '../../lib/adminRoleLabels';

export function RoleSelect({
  user,
  value,
  onChange,
  customRoles = [],
  disabled = false,
  className,
  id = 'role',
  name = 'roleSelection',
}) {
  const { t } = useTranslation();
  const selected = value ?? roleSelectionFromUser(user);

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
      <option value="member">{t('admin.roleMember')}</option>
      {customRoles.map((role) => (
        <option key={role.id} value={role.id}>
          {role.name}
        </option>
      ))}
    </Select>
  );
}
