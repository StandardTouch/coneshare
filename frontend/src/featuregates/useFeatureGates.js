import { useBranding } from '../contexts/BrandingProvider';
import { useUser } from '../contexts/UserProvider';

export function useFeatureGates() {
  const {
    mcpEnabled,
    apiKeysEnabled,
    automationEnabled,
  } = useBranding();
  const { user } = useUser();
  const isAdmin = user?.role === 'admin';

  return {
    mcpEnabled: Boolean(mcpEnabled),
    apiKeysEnabled: Boolean(apiKeysEnabled),
    automationEnabled: Boolean(automationEnabled),
    canAccessApiKeys: Boolean(apiKeysEnabled && isAdmin),
    canAccessAutomations: Boolean(automationEnabled && isAdmin),
    canAccessMcpSetup: Boolean(mcpEnabled && apiKeysEnabled && isAdmin),
  };
}
