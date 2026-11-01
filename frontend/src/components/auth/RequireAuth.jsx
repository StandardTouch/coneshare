import { useEffect, useState } from "react";
import { Navigate, useLocation } from "react-router-dom";
import { useUser } from "../../contexts/UserProvider";

function AuthLoadingSpinner() {
  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50 dark:bg-gray-900">
      <div className="h-8 w-8 animate-spin rounded-full border-2 border-indigo-600 border-t-transparent" />
    </div>
  );
}

function RequireAuth({ children, adminOnly = false }) {
  const { user, isLoading, refreshUser } = useUser();
  const location = useLocation();
  const hasAccessToken = Boolean(localStorage.getItem("access_token"));
  const [tokenRefreshAttempted, setTokenRefreshAttempted] = useState(
    () => !hasAccessToken
  );

  useEffect(() => {
    if (user || isLoading || tokenRefreshAttempted || !hasAccessToken) {
      return;
    }

    let cancelled = false;

    const attemptRefresh = async () => {
      await refreshUser();
      if (!cancelled) {
        setTokenRefreshAttempted(true);
      }
    };

    attemptRefresh();

    return () => {
      cancelled = true;
    };
  }, [user, isLoading, hasAccessToken, tokenRefreshAttempted, refreshUser]);

  const awaitingTokenRefresh = hasAccessToken && !user && !tokenRefreshAttempted;
  const showAuthSpinner = !user && (isLoading || awaitingTokenRefresh);

  if (showAuthSpinner) {
    return <AuthLoadingSpinner />;
  }

  if (!user) {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  if (adminOnly && user.role !== "admin") {
    return <Navigate to="/" replace />;
  }

  return children;
}

export default RequireAuth;
