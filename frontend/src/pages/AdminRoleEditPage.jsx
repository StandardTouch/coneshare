import { useCallback, useEffect, useMemo, useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { toast } from 'sonner';
import { ArrowLeft, Loader2 } from 'lucide-react';

import * as api from '../services/api';
import { AdminNav } from '../components/admin/AdminNav';
import { Button } from '../components/ui/Button';
import { Input } from '../components/ui/Input';
import { Skeleton } from '../components/ui/Skeleton';

const SCOPE_OPTIONS = [
  { value: 'any', label: 'Any' },
  { value: 'own', label: 'Own' },
];

function grantsFromRole(role) {
  const map = {};
  (role?.permission_grants || []).forEach((g) => {
    map[g.permission] = g.scope || 'any';
  });
  return map;
}

export function AdminRoleEditPage() {
  const { t } = useTranslation();
  const { roleId } = useParams();
  const navigate = useNavigate();
  const [role, setRole] = useState(null);
  const [permissions, setPermissions] = useState([]);
  const [draftGrants, setDraftGrants] = useState({});
  const [editMeta, setEditMeta] = useState({ name: '', description: '' });
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);

  const load = useCallback(async () => {
    setIsLoading(true);
    try {
      const [roleRes, catalogRes] = await Promise.all([
        api.getAdminRbacRole(roleId),
        api.getAdminRbacPermissionCatalog(),
      ]);
      setRole(roleRes.data);
      setEditMeta({
        name: roleRes.data.name || '',
        description: roleRes.data.description || '',
      });
      setDraftGrants(grantsFromRole(roleRes.data));
      setPermissions(catalogRes.data?.permissions || []);
    } catch {
      toast.error(t('admin.roles.loadError', { defaultValue: 'Could not load role.' }));
      navigate('/admin/roles');
    } finally {
      setIsLoading(false);
    }
  }, [navigate, roleId, t]);

  useEffect(() => {
    load();
  }, [load]);

  const groupedSections = useMemo(() => {
    const sections = [];
    const byKey = {};
    permissions.forEach((p) => {
      const sectionKey = p.group || p.category || 'other';
      if (!byKey[sectionKey]) {
        byKey[sectionKey] = [];
        sections.push(sectionKey);
      }
      byKey[sectionKey].push(p);
    });
    return { sections, byKey };
  }, [permissions]);

  const togglePermission = (permission, supportsScope) => {
    setDraftGrants((prev) => {
      const next = { ...prev };
      if (next[permission]) {
        delete next[permission];
      } else {
        next[permission] = supportsScope ? 'own' : 'any';
      }
      return next;
    });
  };

  const setScope = (permission, scope) => {
    setDraftGrants((prev) => ({ ...prev, [permission]: scope || 'any' }));
  };

  const handleSave = async () => {
    setIsSaving(true);
    try {
      if (!role?.is_system) {
        await api.updateAdminRbacRole(roleId, {
          name: editMeta.name,
          description: editMeta.description,
        });
      }
      const grants = Object.entries(draftGrants).map(([permission, scope]) => ({
        permission,
        scope: scope === 'any' ? '' : scope,
      }));
      await api.updateAdminRbacRolePermissions(roleId, { grants });
      toast.success(t('admin.roles.saveSuccess', { defaultValue: 'Role saved.' }));
      await load();
    } catch {
      // interceptor
    } finally {
      setIsSaving(false);
    }
  };

  if (isLoading) {
    return (
      <div className="container mx-auto py-6">
        <AdminNav />
        <Skeleton className="h-64 w-full" />
      </div>
    );
  }

  if (!role) return null;

  return (
    <div className="container mx-auto py-6 max-w-4xl">
      <AdminNav />

      <div className="mb-6">
        <Link to="/admin/roles" className="inline-flex items-center text-sm text-muted-foreground hover:text-primary mb-3">
          <ArrowLeft className="mr-2 h-4 w-4" />
          {t('admin.roles.backToList', { defaultValue: 'Back to roles' })}
        </Link>
        <h1 className="text-2xl font-bold tracking-tight">{role.name}</h1>
        <p className="text-sm text-muted-foreground mt-1">
          {role.is_system
            ? t('admin.roles.systemRoleHint', { defaultValue: 'System role — permissions are editable; name is fixed.' })
            : t('admin.roles.customRoleHint', { defaultValue: 'Custom organization role.' })}
        </p>
      </div>

      {!role.is_system && (
        <div className="rounded-lg border p-4 mb-6 space-y-3">
          <div>
            <label className="text-sm font-medium" htmlFor="role-name">
              {t('admin.roles.name', { defaultValue: 'Name' })}
            </label>
            <Input
              id="role-name"
              className="mt-1"
              value={editMeta.name}
              onChange={(e) => setEditMeta((p) => ({ ...p, name: e.target.value }))}
              disabled={isSaving}
            />
          </div>
          <div>
            <label className="text-sm font-medium" htmlFor="role-desc">
              {t('admin.roles.description', { defaultValue: 'Description' })}
            </label>
            <Input
              id="role-desc"
              className="mt-1"
              value={editMeta.description}
              onChange={(e) => setEditMeta((p) => ({ ...p, description: e.target.value }))}
              disabled={isSaving}
            />
          </div>
        </div>
      )}

      <div className="space-y-6">
        {groupedSections.sections.map((sectionKey) => {
          const perms = groupedSections.byKey[sectionKey];
          return (
          <div key={sectionKey} className="rounded-lg border p-4">
            <h2 className="font-semibold mb-3">{sectionKey}</h2>
            <ul className="space-y-3">
              {perms.map((perm) => {
                const enabled = Boolean(draftGrants[perm.codename]);
                const scope = draftGrants[perm.codename] || 'any';
                return (
                  <li key={perm.codename} className="flex flex-wrap items-center gap-3 text-sm">
                    <label className="flex items-center gap-2 min-w-[240px]">
                      <input
                        type="checkbox"
                        checked={enabled}
                        onChange={() => togglePermission(perm.codename, perm.supports_scope)}
                      />
                      <span>
                        <span className="font-medium">{perm.label}</span>
                        <span className="block text-xs text-muted-foreground">{perm.codename}</span>
                      </span>
                    </label>
                    {enabled && perm.supports_scope && (
                      <select
                        className="rounded border bg-background px-2 py-1 text-xs"
                        value={scope === 'own' ? 'own' : 'any'}
                        onChange={(e) => setScope(perm.codename, e.target.value)}
                      >
                        {SCOPE_OPTIONS.map((o) => (
                          <option key={o.value} value={o.value}>
                            {o.label}
                          </option>
                        ))}
                      </select>
                    )}
                  </li>
                );
              })}
            </ul>
          </div>
          );
        })}
      </div>

      <div className="mt-6 flex gap-2">
        <Button onClick={handleSave} disabled={isSaving}>
          {isSaving && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
          {t('common.save')}
        </Button>
        <Button variant="outline" onClick={() => navigate('/admin/roles')} disabled={isSaving}>
          {t('common.cancel')}
        </Button>
      </div>
    </div>
  );
}
