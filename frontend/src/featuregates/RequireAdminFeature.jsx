import { Navigate } from 'react-router';
import { useFeatureGates } from './useFeatureGates';

/** Route guard: admin role and feature toggle required. */
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

/** Route guard: file requests feature toggle (any authenticated user). */
export function RequireFileRequestsFeature({ children }) {
  const { canAccessFileRequests } = useFeatureGates();

  if (!canAccessFileRequests) {
    return <Navigate to="/" replace />;
  }

  return children;
}
