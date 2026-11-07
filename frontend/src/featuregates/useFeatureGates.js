import { useBranding } from '../contexts/BrandingProvider';
import { useUser } from '../contexts/UserProvider';

export function useFeatureGates() {
  const {
    swaggerEnabled,
    apiKeysEnabled,
    automationEnabled,
    fileRequestsEnabled,
    esignEnabled,
    documentsEnabled,
    trashEnabled,
  } = useBranding();
  const { user } = useUser();

  const isAuthenticated = Boolean(user);

  return {
    canAccessFileRequests: isAuthenticated && fileRequestsEnabled !== false,
    canAccessApiKeys: isAuthenticated && apiKeysEnabled !== false,
    canAccessAutomations: isAuthenticated && automationEnabled !== false,
    canAccessMcpSetup: isAuthenticated && apiKeysEnabled !== false,
    canAccessApiDocs: isAuthenticated && swaggerEnabled !== false,
    canAccessDocuments: isAuthenticated && documentsEnabled !== false,
    canAccessTrash: isAuthenticated && trashEnabled !== false,
    canAccessSignatures: esignEnabled !== false,
  };
}
