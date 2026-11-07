import { useCallback, useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { toast } from 'sonner';
import { Loader2, Lock, Pencil, Plus, RotateCcw, Trash2 } from 'lucide-react';

import * as api from '../services/api';
import { getLocalizedErrorMessage } from '../utils/errorTranslator';
import { AdminNav } from '../components/admin/AdminNav';
import { Button } from '../components/ui/Button';
import { Input } from '../components/ui/Input';
import { Skeleton } from '../components/ui/Skeleton';
import { ConfirmationDialog } from '../components/dialogs/ConfirmationDialog';

export function AdminRolesPage() {
  const { t } = useTranslation();
  const [roles, setRoles] = useState([]);
  const [pagination, setPagination] = useState({ count: 0, current_page: 1, total_pages: 1 });
  const [search, setSearch] = useState('');
  const [searchInput, setSearchInput] = useState('');
  const [isLoading, setIsLoading] = useState(true);
  const [showCreate, setShowCreate] = useState(false);
  const [createForm, setCreateForm] = useState({ name: '', description: '' });
  const [isSaving, setIsSaving] = useState(false);
  const [deleteTarget, setDeleteTarget] = useState(null);
  const [isResetting, setIsResetting] = useState(false);
  const [auditLog, setAuditLog] = useState([]);
  const [auditLoading, setAuditLoading] = useState(true);

  const loadRoles = useCallback(
    async (page = 1) => {
      setIsLoading(true);
      try {
        const res = await api.getAdminRbacRoles({ page, search: search || undefined, page_size: 20 });
        setRoles(res.data.results || res.data || []);
        if (res.data.count !== undefined) {
          setPagination({
            count: res.data.count,
            current_page: res.data.current_page,
            total_pages: res.data.total_pages,
          });
        }
      } catch {
        // interceptor
      } finally {
        setIsLoading(false);
      }
    },
    [search]
  );

  const loadAuditLog = useCallback(async () => {
    setAuditLoading(true);
    try {
      const res = await api.getAdminRbacAuditLog();
      setAuditLog(res.data || []);
    } catch {
      setAuditLog([]);
    } finally {
      setAuditLoading(false);
    }
  }, []);

  useEffect(() => {
    loadRoles(1);
    loadAuditLog();
  }, [loadRoles, loadAuditLog]);

  const handleSearch = (e) => {
    e.preventDefault();
    setSearch(searchInput.trim());
  };

  const handleCreate = async (e) => {
    e.preventDefault();
    setIsSaving(true);
    try {
      await api.createAdminRbacRole(createForm);
      toast.success(t('admin.roles.createSuccess', { defaultValue: 'Role created.' }));
      setCreateForm({ name: '', description: '' });
      setShowCreate(false);
      await loadRoles(pagination.current_page);
      await loadAuditLog();
    } catch (err) {
      toast.error(
        getLocalizedErrorMessage(
          err,
          t('admin.roles.createFailed', { defaultValue: 'Could not create role.' })
        )
      );
    } finally {
      setIsSaving(false);
    }
  };

  const handleDelete = async () => {
    if (!deleteTarget) return;
    setIsSaving(true);
    try {
      await api.deleteAdminRbacRole(deleteTarget.id);
      toast.success(t('admin.roles.deleteSuccess', { defaultValue: 'Role deleted.' }));
      setDeleteTarget(null);
      await loadRoles(pagination.current_page);
      await loadAuditLog();
    } catch {
      // interceptor
    } finally {
      setIsSaving(false);
    }
  };

  const handleReset = async () => {
    setIsResetting(true);
    try {
      await api.resetAdminRbacDefaults();
      toast.success(t('admin.rbac.resetDone', { defaultValue: 'System roles reset to defaults.' }));
      await loadRoles(pagination.current_page);
      await loadAuditLog();
    } catch {
      // interceptor
    } finally {
      setIsResetting(false);
    }
  };

  return (
    <div className="container mx-auto py-6">
      <AdminNav />

      <div className="mb-6 flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">
            {t('admin.roles.title', { defaultValue: 'Roles' })}
          </h1>
          <p className="mt-1 max-w-3xl text-sm text-muted-foreground">
            {t('admin.roles.subtitle', {
              defaultValue:
                'Manage organization roles and permissions. Roles apply to users and as defaults when inviting dataroom collaborators.',
            })}
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Button variant="outline" onClick={handleReset} disabled={isLoading || isResetting}>
            {isResetting ? <Loader2 className="h-4 w-4 animate-spin" /> : <RotateCcw className="mr-2 h-4 w-4" />}
            {t('admin.rbac.resetDefaults', { defaultValue: 'Reset system roles' })}
          </Button>
          <Button onClick={() => setShowCreate(true)}>
            <Plus className="mr-2 h-4 w-4" />
            {t('admin.roles.create', { defaultValue: 'Create role' })}
          </Button>
        </div>
      </div>

      <form onSubmit={handleSearch} className="mb-4 flex gap-2 max-w-md">
        <Input
          value={searchInput}
          onChange={(e) => setSearchInput(e.target.value)}
          placeholder={t('admin.roles.searchPlaceholder', { defaultValue: 'Search roles…' })}
        />
        <Button type="submit" variant="secondary">
          {t('common.search', { defaultValue: 'Search' })}
        </Button>
      </form>

      {isLoading ? (
        <Skeleton className="h-48 w-full" />
      ) : (
        <div className="overflow-x-auto rounded-lg border mb-8">
          <table className="w-full text-sm">
            <thead className="bg-muted/50">
              <tr className="border-b text-left">
                <th className="p-3">{t('admin.roles.name', { defaultValue: 'Name' })}</th>
                <th className="p-3">{t('admin.roles.description', { defaultValue: 'Description' })}</th>
                <th className="p-3">{t('admin.roles.users', { defaultValue: 'Users' })}</th>
                <th className="p-3">{t('admin.roles.type', { defaultValue: 'Type' })}</th>
                <th className="p-3 w-32" />
              </tr>
            </thead>
            <tbody>
              {roles.map((role) => (
                <tr key={role.id} className="border-b">
                  <td className="p-3 font-medium">
                    <span className="inline-flex items-center gap-2">
                      {role.name}
                      {role.is_system && <Lock className="h-3.5 w-3.5 text-muted-foreground" aria-hidden />}
                    </span>
                  </td>
                  <td className="p-3 text-muted-foreground max-w-md truncate">{role.description || '—'}</td>
                  <td className="p-3">{role.user_count ?? 0}</td>
                  <td className="p-3">
                    {role.is_system
                      ? t('admin.roles.system', { defaultValue: 'System' })
                      : t('admin.roles.custom', { defaultValue: 'Custom' })}
                  </td>
                  <td className="p-3">
                    <div className="flex gap-1">
                      <Button asChild size="sm" variant="ghost">
                        <Link to={`/admin/roles/${role.id}`}>
                          <Pencil className="h-4 w-4" />
                        </Link>
                      </Button>
                      {!role.is_system && (
                        <Button
                          size="sm"
                          variant="ghost"
                          onClick={() => setDeleteTarget(role)}
                          aria-label={t('admin.roles.delete', { defaultValue: 'Delete' })}
                        >
                          <Trash2 className="h-4 w-4" />
                        </Button>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {pagination.total_pages > 1 && (
        <div className="flex gap-2 mb-8">
          <Button
            variant="outline"
            size="sm"
            disabled={pagination.current_page <= 1 || isLoading}
            onClick={() => loadRoles(pagination.current_page - 1)}
          >
            {t('common.previous', { defaultValue: 'Previous' })}
          </Button>
          <span className="text-sm self-center text-muted-foreground">
            {pagination.current_page} / {pagination.total_pages}
          </span>
          <Button
            variant="outline"
            size="sm"
            disabled={pagination.current_page >= pagination.total_pages || isLoading}
            onClick={() => loadRoles(pagination.current_page + 1)}
          >
            {t('common.next', { defaultValue: 'Next' })}
          </Button>
        </div>
      )}

      <div className="rounded-lg border p-4 space-y-3">
        <h2 className="font-semibold">{t('admin.rbac.auditTitle', { defaultValue: 'Audit log' })}</h2>
        {auditLoading ? (
          <Skeleton className="h-24 w-full" />
        ) : auditLog.length === 0 ? (
          <p className="text-sm text-muted-foreground">{t('admin.rbac.auditEmpty', { defaultValue: 'No entries yet.' })}</p>
        ) : (
          <div className="overflow-x-auto max-h-60 overflow-y-auto">
            <table className="w-full text-sm">
              <tbody>
                {auditLog.map((entry) => (
                  <tr key={entry.id} className="border-b">
                    <td className="py-2 pr-3 text-xs whitespace-nowrap">
                      {entry.created_at ? new Date(entry.created_at).toLocaleString() : '—'}
                    </td>
                    <td className="py-2 pr-3 text-xs">{entry.actor_email || '—'}</td>
                    <td className="py-2">{entry.summary}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {showCreate && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
          <form
            onSubmit={handleCreate}
            className="w-full max-w-md rounded-lg border bg-background p-6 shadow-lg space-y-4"
          >
            <h2 className="text-lg font-semibold">{t('admin.roles.create', { defaultValue: 'Create role' })}</h2>
            <Input
              required
              value={createForm.name}
              onChange={(e) => setCreateForm((p) => ({ ...p, name: e.target.value }))}
              placeholder={t('admin.roles.name', { defaultValue: 'Name' })}
              disabled={isSaving}
            />
            <Input
              value={createForm.description}
              onChange={(e) => setCreateForm((p) => ({ ...p, description: e.target.value }))}
              placeholder={t('admin.roles.description', { defaultValue: 'Description' })}
              disabled={isSaving}
            />
            <div className="flex justify-end gap-2">
              <Button type="button" variant="outline" onClick={() => setShowCreate(false)} disabled={isSaving}>
                {t('common.cancel')}
              </Button>
              <Button type="submit" disabled={isSaving}>
                {isSaving && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                {t('common.create', { defaultValue: 'Create' })}
              </Button>
            </div>
          </form>
        </div>
      )}

      <ConfirmationDialog
        isOpen={Boolean(deleteTarget)}
        onOpenChange={(open) => {
          if (!open) setDeleteTarget(null);
        }}
        onConfirm={handleDelete}
        title={t('admin.roles.deleteTitle', { defaultValue: 'Delete role?' })}
        description={t('admin.roles.deleteDescription', {
          defaultValue: 'Users and collaborators must be reassigned before this role can be deleted.',
        })}
        isLoading={isSaving}
      />
    </div>
  );
}
