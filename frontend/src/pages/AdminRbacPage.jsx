import { useCallback, useEffect, useMemo, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { toast } from 'sonner';
import { Loader2, RotateCcw } from 'lucide-react';

import * as api from '../services/api';
import { AdminNav } from '../components/admin/AdminNav';
import { Button } from '../components/ui/Button';
import { Skeleton } from '../components/ui/Skeleton';

const SCOPE_OPTIONS = [
  { value: '', label: '—' },
  { value: 'any', label: 'Any' },
  { value: 'own', label: 'Own' },
];

function grantsFromRole(role) {
  const map = {};
  (role.permission_grants || []).forEach((g) => {
    map[g.permission] = g.scope || 'any';
  });
  return map;
}

export function AdminRbacPage() {
  const { t } = useTranslation();
  const [matrix, setMatrix] = useState(null);
  const [draftGrants, setDraftGrants] = useState({});
  const [siteDraft, setSiteDraft] = useState({ admin: [], member: [] });
  const [isLoading, setIsLoading] = useState(true);
  const [savingRoleId, setSavingRoleId] = useState(null);
  const [isResetting, setIsResetting] = useState(false);
  const [auditLog, setAuditLog] = useState([]);
  const [auditLoading, setAuditLoading] = useState(true);

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

  const loadMatrix = useCallback(async () => {
    setIsLoading(true);
    try {
      const res = await api.getAdminRbacMatrix();
      setMatrix(res.data);
      const nextDraft = {};
      (res.data.roles || []).forEach((role) => {
        nextDraft[role.id] = grantsFromRole(role);
      });
      setDraftGrants(nextDraft);
      setSiteDraft({
        admin: res.data.site_permissions?.admin || [],
        member: res.data.site_permissions?.member || [],
      });
    } catch {
      // interceptor
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    loadMatrix();
    loadAuditLog();
  }, [loadMatrix, loadAuditLog]);

  const permissions = matrix?.permissions || [];

  const togglePermission = (roleId, permission, supportsScope) => {
    setDraftGrants((prev) => {
      const roleGrants = { ...(prev[roleId] || {}) };
      if (roleGrants[permission]) {
        delete roleGrants[permission];
      } else {
        roleGrants[permission] = supportsScope ? 'own' : 'any';
      }
      return { ...prev, [roleId]: roleGrants };
    });
  };

  const setScope = (roleId, permission, scope) => {
    setDraftGrants((prev) => ({
      ...prev,
      [roleId]: { ...(prev[roleId] || {}), [permission]: scope || 'any' },
    }));
  };

  const saveRole = async (role) => {
    setSavingRoleId(role.id);
    try {
      const grants = Object.entries(draftGrants[role.id] || {}).map(([permission, scope]) => ({
        permission,
        scope,
      }));
      await api.updateAdminRbacRolePermissions(role.id, { grants });
      toast.success(t('admin.rbac.saved', { defaultValue: 'Role permissions updated.' }));
      await loadMatrix();
      await loadAuditLog();
    } catch {
      // interceptor
    } finally {
      setSavingRoleId(null);
    }
  };

  const saveSitePermissions = async (siteRole) => {
    setSavingRoleId(`site-${siteRole}`);
    try {
      await api.updateAdminSitePermissions({
        site_role: siteRole,
        permissions: siteDraft[siteRole] || [],
      });
      toast.success(t('admin.rbac.siteSaved', { defaultValue: 'Site permissions updated.' }));
      await loadMatrix();
      await loadAuditLog();
    } catch {
      // interceptor
    } finally {
      setSavingRoleId(null);
    }
  };

  const handleReset = async () => {
    setIsResetting(true);
    try {
      await api.resetAdminRbacDefaults();
      toast.success(t('admin.rbac.resetDone', { defaultValue: 'System roles reset to defaults.' }));
      await loadMatrix();
      await loadAuditLog();
    } catch {
      // interceptor
    } finally {
      setIsResetting(false);
    }
  };

  const roles = useMemo(() => matrix?.roles || [], [matrix]);

  return (
    <div className="container mx-auto py-6">
      <AdminNav />

      <div className="mb-6 flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">
            {t('admin.rbac.title', { defaultValue: 'Roles & Permissions' })}
          </h1>
          <p className="mt-1 max-w-3xl text-sm text-muted-foreground">
            {t('admin.rbac.subtitle', {
              defaultValue:
                'Configure dataroom roles and site-level create permissions. User role labels on the Users page remain display-only.',
            })}
          </p>
          {matrix?.role_labels_note && (
            <p className="mt-2 text-xs text-muted-foreground">{matrix.role_labels_note}</p>
          )}
        </div>
        <Button variant="outline" onClick={handleReset} disabled={isLoading || isResetting}>
          {isResetting ? <Loader2 className="h-4 w-4 animate-spin" /> : <RotateCcw className="mr-2 h-4 w-4" />}
          {t('admin.rbac.resetDefaults', { defaultValue: 'Reset system roles' })}
        </Button>
      </div>

      {isLoading ? (
        <Skeleton className="h-64 w-full" />
      ) : (
        <div className="space-y-8">
          <div className="overflow-x-auto rounded-lg border">
            <table className="min-w-[960px] w-full text-sm">
              <thead className="bg-muted/50">
                <tr className="border-b text-left">
                  <th className="p-3 w-56">{t('admin.rbac.permission', { defaultValue: 'Permission' })}</th>
                  {roles.map((role) => (
                    <th key={role.id} className="p-3 min-w-[140px]">
                      <div className="font-semibold">{role.name}</div>
                      {role.is_system && (
                        <div className="text-[11px] text-muted-foreground">{role.slug}</div>
                      )}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {permissions.map((perm) => (
                  <tr key={perm.codename} className="border-b align-top">
                    <td className="p-3">
                      <div className="font-medium">{perm.label}</div>
                      <div className="text-[11px] text-muted-foreground">{perm.codename}</div>
                    </td>
                    {roles.map((role) => {
                      const enabled = Boolean(draftGrants[role.id]?.[perm.codename]);
                      const scope = draftGrants[role.id]?.[perm.codename] || '';
                      return (
                        <td key={`${role.id}-${perm.codename}`} className="p-3">
                          <label className="flex items-center gap-2">
                            <input
                              type="checkbox"
                              checked={enabled}
                              onChange={() => togglePermission(role.id, perm.codename, perm.supports_scope)}
                            />
                            {enabled && perm.supports_scope && (
                              <select
                                className="rounded border bg-background px-1 py-0.5 text-xs"
                                value={scope === 'any' ? 'any' : 'own'}
                                onChange={(e) => setScope(role.id, perm.codename, e.target.value)}
                              >
                                {SCOPE_OPTIONS.filter((o) => o.value).map((o) => (
                                  <option key={o.value} value={o.value}>
                                    {o.label}
                                  </option>
                                ))}
                              </select>
                            )}
                          </label>
                        </td>
                      );
                    })}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <div className="flex flex-wrap gap-2">
            {roles.map((role) => (
              <Button
                key={role.id}
                size="sm"
                variant="secondary"
                disabled={savingRoleId === role.id}
                onClick={() => saveRole(role)}
              >
                {savingRoleId === role.id && <Loader2 className="mr-2 h-3.5 w-3.5 animate-spin" />}
                {t('admin.rbac.saveRole', { defaultValue: 'Save {{name}}', name: role.name })}
              </Button>
            ))}
          </div>

          <div className="rounded-lg border p-4 space-y-4 max-w-xl">
            <h2 className="font-semibold">{t('admin.rbac.siteTitle', { defaultValue: 'Site permissions' })}</h2>
            {['admin', 'member'].map((siteRole) => (
              <div key={siteRole} className="flex items-center justify-between gap-4">
                <span className="capitalize text-sm">{siteRole}</span>
                <label className="flex items-center gap-2 text-sm">
                  <input
                    type="checkbox"
                    checked={(siteDraft[siteRole] || []).includes('create_dataroom')}
                    onChange={(e) => {
                      setSiteDraft((prev) => ({
                        ...prev,
                        [siteRole]: e.target.checked ? ['create_dataroom'] : [],
                      }));
                    }}
                  />
                  {t('admin.rbac.createDataroom', { defaultValue: 'Create datarooms' })}
                </label>
                <Button
                  size="sm"
                  variant="outline"
                  disabled={savingRoleId === `site-${siteRole}`}
                  onClick={() => saveSitePermissions(siteRole)}
                >
                  {t('common.save')}
                </Button>
              </div>
            ))}
          </div>

          <div className="rounded-lg border p-4 space-y-3">
            <h2 className="font-semibold">{t('admin.rbac.auditTitle', { defaultValue: 'Audit log' })}</h2>
            <p className="text-xs text-muted-foreground">
              {t('admin.rbac.auditSubtitle', {
                defaultValue: 'Recent permission and role changes in your organization.',
              })}
            </p>
            {auditLoading ? (
              <Skeleton className="h-32 w-full" />
            ) : auditLog.length === 0 ? (
              <p className="text-sm text-muted-foreground">{t('admin.rbac.auditEmpty', { defaultValue: 'No entries yet.' })}</p>
            ) : (
              <div className="overflow-x-auto max-h-80 overflow-y-auto">
                <table className="w-full text-sm">
                  <thead className="sticky top-0 bg-background border-b">
                    <tr className="text-left text-muted-foreground">
                      <th className="py-2 pr-3">{t('admin.rbac.auditWhen', { defaultValue: 'When' })}</th>
                      <th className="py-2 pr-3">{t('admin.rbac.auditWho', { defaultValue: 'Who' })}</th>
                      <th className="py-2 pr-3">{t('admin.rbac.auditWhat', { defaultValue: 'What' })}</th>
                    </tr>
                  </thead>
                  <tbody>
                    {auditLog.map((entry) => (
                      <tr key={entry.id} className="border-b align-top">
                        <td className="py-2 pr-3 whitespace-nowrap text-xs">
                          {entry.created_at ? new Date(entry.created_at).toLocaleString() : '—'}
                        </td>
                        <td className="py-2 pr-3 text-xs">
                          {entry.actor_email || t('admin.rbac.systemActor', { defaultValue: 'System' })}
                        </td>
                        <td className="py-2 pr-3">{entry.summary}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
