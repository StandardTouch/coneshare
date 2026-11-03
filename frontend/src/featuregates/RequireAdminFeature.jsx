import { Navigate } from 'react-router';
import { useFeatureGates } from './useFeatureGates';

/**
 * Route guard: feature must be enabled and user must be admin.
 */
export default function RequireAdminFeature({ feature, children }) {
  const gates = useFeatureGates();

  const allowed =
    feature === 'apiKeys'
      ? gates.canAccessApiKeys
      : feature === 'automation'
        ? gates.canAccessAutomations
        : false;

  if (!allowed) {
    return <Navigate to="/" replace />;
  }

  return children;
}
