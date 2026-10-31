import { useCallback, useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { toast } from 'sonner';
import { Lock, Pencil, Plus, Trash2, X, Check, Loader2 } from 'lucide-react';

import * as api from '../services/api';
import { AdminNav } from '../components/admin/AdminNav';
import { Button } from '../components/ui/Button';
import { Input } from '../components/ui/Input';
import { Skeleton } from '../components/ui/Skeleton';
import { ConfirmationDialog } from '../components/dialogs/ConfirmationDialog';

export function AdminRolesPage() {
  const { t } = useTranslation();
  const [systemRoles, setSystemRoles] = useState([]);
  const [customRoles, setCustomRoles] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [showCreate, setShowCreate] = useState(false);
  const [createForm, setCreateForm] = useState({ name: '', description: '' });
  const [isSaving, setIsSaving] = useState(false);
  const [editingId, setEditingId] = useState(null);
  const [editForm, setEditForm] = useState({ name: '', description: '' });
  const [deleteTarget, setDeleteTarget] = useState(null);

  const loadRoles = useCallback(async () => {
    setIsLoading(true);
    try {
      const res = await api.getAdminRoleLabels();
      setSystemRoles(res.data.system_roles || []);
      setCustomRoles(res.data.custom_roles || []);
    } catch {
      // handled by interceptor
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    loadRoles();
  }, [loadRoles]);

  const handleCreate = async (e) => {
    e.preventDefault();
    setIsSaving(true);
    try {
      await api.createAdminRoleLabel(createForm);
      toast.success(t('admin.roles.createSuccess', { defaultValue: 'Role created.' }));
      setCreateForm({ name: '', description: '' });
      setShowCreate(false);
      await loadRoles();
    } catch {
      // interceptor
    } finally {
      setIsSaving(false);
    }
  };

  const startEdit = (role) => {
    setEditingId(role.id);
    setEditForm({ name: role.name, description: role.description || '' });
  };

  const handleSaveEdit = async (roleId) => {
    setIsSaving(true);
    try {
      await api.updateAdminRoleLabel(roleId, editForm);
      toast.success(t('admin.roles.updateSuccess', { defaultValue: 'Role updated.' }));
      setEditingId(null);
      await loadRoles();
    } catch {
      // interceptor
    } finally {
      setIsSaving(false);
    }
  };

  const handleDelete = async () => {
    if (!deleteTarget) return;
    setIsSaving(true);
    try {
      await api.deleteAdminRoleLabel(deleteTarget.id);
      toast.success(t('admin.roles.deleteSuccess', { defaultValue: 'Role deleted.' }));
      setDeleteTarget(null);
      await loadRoles();
    } catch {
      // interceptor
    } finally {
      setIsSaving(false);
    }
  };

  const renderRoleRow = (role, { isSystem }) => (
    <tr key={role.id} className="border-b">
      <td className="p-4 font-medium">
        {isSystem ? (
          <span className="flex items-center gap-2">
            {role.name}
            <Lock className="h-3.5 w-3.5 text-muted-foreground" aria-hidden />
          </span>
        ) : editingId === role.id ? (
          <Input
            value={editForm.name}
            onChange={(e) => setEditForm((p) => ({ ...p, name: e.target.value }))}
            disabled={isSaving}
          />
        ) : (
          role.name
        )}
      </td>
      <td className="p-4 text-muted-foreground max-w-md">
        {isSystem ? (
          role.description
        ) : editingId === role.id ? (
          <Input
            value={editForm.description}
            onChange={(e) => setEditForm((p) => ({ ...p, description: e.target.value }))}
            disabled={isSaving}
          />
        ) : (
          role.description || '—'
        )}
      </td>
      <td className="p-4 text-muted-foreground w-24">{role.user_count ?? '—'}</td>
      <td className="p-4 text-right w-32">
        {isSystem ? (
          <span className="text-xs text-muted-foreground">{t('admin.roles.systemRole', { defaultValue: 'System' })}</span>
        ) : editingId === role.id ? (
          <div className="flex justify-end gap-2">
            <Button size="sm" variant="ghost" onClick={() => setEditingId(null)} disabled={isSaving}>
              <X className="h-4 w-4" />
            </Button>
            <Button size="sm" onClick={() => handleSaveEdit(role.id)} disabled={isSaving}>
              {isSaving ? <Loader2 className="h-4 w-4 animate-spin" /> : <Check className="h-4 w-4" />}
            </Button>
          </div>
        ) : (
          <div className="flex justify-end gap-2">
            <Button size="sm" variant="ghost" onClick={() => startEdit(role)} disabled={isSaving}>
              <Pencil className="h-4 w-4" />
            </Button>
            <Button size="sm" variant="ghost" onClick={() => setDeleteTarget(role)} disabled={isSaving}>
              <Trash2 className="h-4 w-4 text-destructive" />
            </Button>
          </div>
        )}
      </td>
    </tr>
  );

  return (
    <div className="container mx-auto py-6">
      <AdminNav />

      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">{t('admin.roles.title', { defaultValue: 'Roles' })}</h1>
          <p className="text-sm text-muted-foreground mt-1">
            {t('admin.roles.subtitle', {
              defaultValue: 'Custom roles are display labels only; permissions follow the Member role.',
            })}
          </p>
        </div>
        <Button onClick={() => setShowCreate((v) => !v)} disabled={isLoading}>
          <Plus className="mr-2 h-4 w-4" />
          {t('admin.roles.addRole', { defaultValue: 'Add role' })}
        </Button>
      </div>

      {showCreate && (
        <form onSubmit={handleCreate} className="mb-6 rounded-lg border bg-card p-4 space-y-4">
          <div className="grid gap-4 md:grid-cols-2">
            <div>
              <label className="mb-1 block text-sm font-medium" htmlFor="new-role-name">
                {t('admin.roles.name', { defaultValue: 'Name' })}
              </label>
              <Input
                id="new-role-name"
                value={createForm.name}
                onChange={(e) => setCreateForm((p) => ({ ...p, name: e.target.value }))}
                required
                disabled={isSaving}
              />
            </div>
            <div>
              <label className="mb-1 block text-sm font-medium" htmlFor="new-role-desc">
                {t('admin.roles.description', { defaultValue: 'Description' })}
              </label>
              <Input
                id="new-role-desc"
                value={createForm.description}
                onChange={(e) => setCreateForm((p) => ({ ...p, description: e.target.value }))}
                disabled={isSaving}
              />
            </div>
          </div>
          <div className="flex gap-2">
            <Button type="submit" disabled={isSaving}>
              {isSaving ? <Loader2 className="h-4 w-4 animate-spin" /> : t('common.save')}
            </Button>
            <Button type="button" variant="outline" onClick={() => setShowCreate(false)} disabled={isSaving}>
              {t('common.cancel')}
            </Button>
          </div>
        </form>
      )}

      {isLoading ? (
        <Skeleton className="h-48 w-full" />
      ) : (
        <div className="rounded-lg border overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-muted/50">
              <tr className="border-b text-left">
                <th className="p-4">{t('admin.roles.name', { defaultValue: 'Name' })}</th>
                <th className="p-4">{t('admin.roles.description', { defaultValue: 'Description' })}</th>
                <th className="p-4 w-24">{t('admin.roles.users', { defaultValue: 'Users' })}</th>
                <th className="p-4 w-32 text-right">{t('common.actions', { defaultValue: 'Actions' })}</th>
              </tr>
            </thead>
            <tbody>
              {systemRoles.map((role) => renderRoleRow(role, { isSystem: true }))}
              {customRoles.map((role) => renderRoleRow(role, { isSystem: false }))}
            </tbody>
          </table>
        </div>
      )}

      <ConfirmationDialog
        isOpen={Boolean(deleteTarget)}
        onOpenChange={(open) => !open && setDeleteTarget(null)}
        title={t('admin.roles.deleteTitle', { defaultValue: 'Delete role?' })}
        description={t('admin.roles.deleteDescription', {
          defaultValue: 'This cannot be undone. Roles assigned to users must be reassigned first.',
        })}
        onConfirm={handleDelete}
        confirmText={t('common.delete')}
        isLoading={isSaving}
      />
    </div>
  );
}
