import { useCallback, useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { toast } from 'sonner';
import { Loader2 } from 'lucide-react';

import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '../ui/Dialog';
import { Button } from '../ui/Button';
import { getDataroomRoleOptions, getFolderAccessRules, setFolderAccessRule } from '../../services/api';

const RULES = [
  { value: 'inherit', labelKey: 'inherit' },
  { value: 'view_only', labelKey: 'viewOnly' },
  { value: 'hidden', labelKey: 'hidden' },
];

export function FolderAccessRulesDialog({ isOpen, onOpenChange, dataroomId, folder, onSaved }) {
  const { t } = useTranslation();
  const [roles, setRoles] = useState([]);
  const [draft, setDraft] = useState({});
  const [isLoading, setIsLoading] = useState(false);
  const [isSaving, setIsSaving] = useState(false);

  const load = useCallback(async () => {
    if (!dataroomId || !folder?.id) return;
    setIsLoading(true);
    try {
      const [rolesRes, rulesRes] = await Promise.all([
        getDataroomRoleOptions(dataroomId),
        getFolderAccessRules(folder.id),
      ]);
      setRoles(rolesRes.data || []);
      const map = {};
      (rulesRes.data || []).forEach((row) => {
        map[row.dataroom_role] = row.rule;
      });
      const next = {};
      (rolesRes.data || []).forEach((role) => {
        next[role.id] = map[role.id] || 'inherit';
      });
      setDraft(next);
    } catch {
      // interceptor
    } finally {
      setIsLoading(false);
    }
  }, [dataroomId, folder?.id]);

  useEffect(() => {
    if (isOpen) {
      load();
    }
  }, [isOpen, load]);

  const handleSave = async () => {
    setIsSaving(true);
    try {
      await Promise.all(
        roles.map((role) =>
          setFolderAccessRule({
            dataroom_folder: folder.id,
            dataroom_role: role.id,
            rule: draft[role.id] || 'inherit',
          })
        )
      );
      toast.success(t('datarooms.folderRulesSaved', { defaultValue: 'Access rules updated.' }));
      onSaved?.();
      onOpenChange(false);
    } catch {
      // interceptor
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <Dialog open={isOpen} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-lg">
        <DialogHeader>
          <DialogTitle>{t('datarooms.folderAccessRulesTitle', { defaultValue: 'Folder access rules' })}</DialogTitle>
          <DialogDescription>
            {t('datarooms.folderAccessRulesDesc', {
              defaultValue: 'Set per-role access for "{{name}}". Subfolders inherit unless overridden.',
              name: folder?.name || '',
            })}
          </DialogDescription>
        </DialogHeader>

        {isLoading ? (
          <div className="flex justify-center py-8">
            <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
          </div>
        ) : (
          <div className="space-y-3 max-h-[50vh] overflow-y-auto">
            {roles.map((role) => (
              <div key={role.id} className="flex items-center justify-between gap-3">
                <span className="text-sm font-medium">{role.name}</span>
                <select
                  className="rounded-md border bg-background px-2 py-1.5 text-sm"
                  value={draft[role.id] || 'inherit'}
                  onChange={(e) => setDraft((prev) => ({ ...prev, [role.id]: e.target.value }))}
                >
                  {RULES.map((opt) => (
                    <option key={opt.value} value={opt.value}>
                      {t(`datarooms.folderRule.${opt.labelKey}`, { defaultValue: opt.value })}
                    </option>
                  ))}
                </select>
              </div>
            ))}
          </div>
        )}

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)} disabled={isSaving}>
            {t('common.cancel')}
          </Button>
          <Button onClick={handleSave} disabled={isSaving || isLoading}>
            {isSaving && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
            {t('common.save')}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
