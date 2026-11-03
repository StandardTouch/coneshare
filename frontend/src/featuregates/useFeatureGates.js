import { useBranding } from '../contexts/BrandingProvider';
import { useUser } from '../contexts/UserProvider';

export function useFeatureGates() {
  const {
    swaggerEnabled,
    apiKeysEnabled,
    automationEnabled,
    fileRequestsEnabled,
  } = useBranding();
  const { user } = useUser();
  const isAdmin = user?.role === 'admin';

  return {
    canAccessFileRequests: fileRequestsEnabled !== false,
    canAccessApiKeys: isAdmin && apiKeysEnabled !== false,
    canAccessAutomations: isAdmin && automationEnabled !== false,
    canAccessMcpSetup: isAdmin && apiKeysEnabled !== false,
    canAccessApiDocs: isAdmin && swaggerEnabled !== false,
  };
}
