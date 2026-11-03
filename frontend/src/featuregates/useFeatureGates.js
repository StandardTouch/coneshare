import { useBranding } from '../contexts/BrandingProvider';
import { useUser } from '../contexts/UserProvider';

export function useFeatureGates() {
  const { swaggerEnabled } = useBranding();
  const { user } = useUser();
  const isAdmin = user?.role === 'admin';

  return {
    canAccessApiKeys: isAdmin,
    canAccessAutomations: isAdmin,
    canAccessMcpSetup: isAdmin,
    canAccessApiDocs: isAdmin && swaggerEnabled !== false,
  };
}
