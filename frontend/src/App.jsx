import { lazy, Suspense } from 'react';
import { Route, Routes } from 'react-router';
import { Toaster } from 'sonner';
import './App.css';
import MainLayout from './components/layout/MainLayout';
import RequireAuth from './components/auth/RequireAuth';
import RequireAdminFeature from './featuregates/RequireAdminFeature';
import { UploadProvider } from './contexts/UploadProvider';
import { UserProvider } from './contexts/UserProvider';
import { BrandingProvider } from './contexts/BrandingProvider';
import { TooltipProvider } from './components/ui/Tooltip';

// Helper for lazy loading named exports
const lazyNamed = (importer, name) =>
  lazy(() => importer().then((module) => ({ default: module[name] })));

// Public / auth routes
const LoginPage = lazy(() => import('./pages/LoginPage'));
const SignupPage = lazyNamed(() => import('./pages/SignupPage'), 'SignupPage');
const SignupVerifyPage = lazyNamed(() => import('./pages/SignupVerifyPage'), 'SignupVerifyPage');
const SetPasswordPage = lazyNamed(() => import('./pages/SetPasswordPage'), 'SetPasswordPage');
const ShareLinkViewerPage = lazyNamed(() => import('./pages/ShareLinkViewerPage'), 'ShareLinkViewerPage');
const PublicUploadPage = lazyNamed(() => import('./pages/PublicUploadPage'), 'PublicUploadPage');
const CloudAuthCallbackPage = lazyNamed(() => import('./pages/CloudAuthCallbackPage'), 'CloudAuthCallbackPage');
const TermsPage = lazyNamed(() => import('./pages/TermsPage'), 'TermsPage');
const PrivacyPage = lazyNamed(() => import('./pages/PrivacyPage'), 'PrivacyPage');
const PublicAppHomePage = lazyNamed(() => import('./pages/PublicAppHomePage'), 'PublicAppHomePage');
const ErrorPage = lazyNamed(() => import('./pages/ErrorPage'), 'ErrorPage');
const NotFoundPage = lazyNamed(() => import('./pages/NotFoundPage'), 'NotFoundPage');

// Authenticated app routes
const HomePage = lazy(() => import('./pages/HomePage'));
const DocumentsPage = lazy(() => import('./pages/DocumentsPage'));
const DocumentPage = lazyNamed(() => import('./pages/DocumentPage'), 'DocumentPage');
const DocumentVersionsPage = lazyNamed(() => import('./pages/DocumentVersionsPage'), 'DocumentVersionsPage');
const ShareLinkAnalyticsPage = lazyNamed(() => import('./pages/ShareLinkAnalyticsPage'), 'ShareLinkAnalyticsPage');
const TrashPage = lazy(() => import('./pages/TrashPage'));
const DataroomsPage = lazyNamed(() => import('./pages/DataroomsPage'), 'DataroomsPage');
const DataroomPage = lazyNamed(() => import('./pages/DataroomPage'), 'DataroomPage');
const FileRequestsPage = lazyNamed(() => import('./pages/FileRequestsPage'), 'FileRequestsPage');
const FileRequestDetailPage = lazyNamed(() => import('./pages/FileRequestDetailPage'), 'FileRequestDetailPage');
const AllLinksPage = lazyNamed(() => import('./pages/AllLinksPage'), 'AllLinksPage');
const AllViewSessionsPage = lazyNamed(() => import('./pages/AllViewSessionsPage'), 'AllViewSessionsPage');
const AutomationsPage = lazyNamed(() => import('./pages/AutomationsPage'), 'AutomationsPage');
const UserSettingsPage = lazy(() => import('./pages/UserSettingsPage'));
const PasswordSettingsPage = lazy(() => import('./pages/PasswordSettingsPage'));
const IntegrationsSettingsPage = lazyNamed(() => import('./pages/IntegrationsSettingsPage'), 'IntegrationsSettingsPage');
const ApiKeysSettingsPage = lazy(() => import('./pages/ApiKeysSettingsPage'));
const AdminSettingsPage = lazyNamed(() => import('./pages/AdminSettingsPage'), 'AdminSettingsPage');
const AdminBrandingPage = lazyNamed(() => import('./pages/AdminBrandingPage'), 'AdminBrandingPage');
const AdminLoginActivityPage = lazyNamed(() => import('./pages/AdminLoginActivityPage'), 'AdminLoginActivityPage');
const AdminUsersPage = lazyNamed(() => import('./pages/AdminUsersPage'), 'AdminUsersPage');
const AdminUserDetailPage = lazyNamed(() => import('./pages/AdminUserDetailPage'), 'AdminUserDetailPage');
const AdminDataroomsPage = lazyNamed(() => import('./pages/AdminDataroomsPage'), 'AdminDataroomsPage');
const AdminRolesPage = lazyNamed(() => import('./pages/AdminRolesPage'), 'AdminRolesPage');
const AdminSecurityAlertsPage = lazyNamed(() => import('./pages/AdminSecurityAlertsPage'), 'AdminSecurityAlertsPage');

// E-signature routes
const SignatureRequestsPage = lazy(() => import('./pages/SignatureRequestsPage'));
const SignatureRequestDetailPage = lazy(() => import('./pages/SignatureRequestDetailPage'));
const SigningPage = lazy(() => import('./pages/SigningPage'));

function RouteLoadingFallback() {
  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50 dark:bg-gray-900">
      <div className="h-8 w-8 animate-spin rounded-full border-2 border-indigo-600 border-t-transparent" />
    </div>
  );
}

function App() {
  return (
    <>
      <Toaster richColors />
      <TooltipProvider>
        <BrandingProvider>
          <UserProvider>
          <UploadProvider>
            <Suspense fallback={<RouteLoadingFallback />}>
              <Routes>
                <Route path="/login" element={<LoginPage />} />
                <Route path="/signup" element={<SignupPage />} />
                <Route path="/signup/verify" element={<SignupVerifyPage />} />
                <Route path="/set-password/:uid/:token" element={<SetPasswordPage />} />
                <Route path="/view/:slug" element={<ShareLinkViewerPage />} />
                <Route path="/upload/:slug" element={<PublicUploadPage />} />
                <Route path="/auth/:providerName/callback" element={<CloudAuthCallbackPage />} />
                <Route path="/welcome" element={<PublicAppHomePage />} />
                <Route path="/terms" element={<TermsPage />} />
                <Route path="/privacy" element={<PrivacyPage />} />
                <Route path="/500" element={<ErrorPage />} />
                {/* E-signature signing page (requires authentication) */}
                <Route element={<RequireAuth><MainLayout /></RequireAuth>}>
                  <Route path="/sign/:token" element={<SigningPage />} />
                </Route>
                <Route element={<RequireAuth><MainLayout /></RequireAuth>}>
                  <Route path="/" element={<HomePage />} />
                  <Route path="/documents" element={<DocumentsPage />} />
                  <Route path="/documents/folders/:folderId" element={<DocumentsPage />} />
                  <Route path="/documents/:documentId" element={<DocumentPage />} />
                  <Route path="/documents/:documentId/versions" element={<DocumentVersionsPage />} />
                  <Route path="/documents/:documentId/links/:linkId" element={<ShareLinkAnalyticsPage />} />
                  <Route path="/trash" element={<TrashPage />} />
                  <Route path="/datarooms" element={<DataroomsPage />} />
                  <Route path="/datarooms/:dataroomId" element={<DataroomPage />} />
                  <Route path="/file-requests" element={<FileRequestsPage />} />
                  <Route path="/file-requests/:requestId" element={<FileRequestDetailPage />} />
                  <Route path="/analytics/links" element={<AllLinksPage />} />
                  <Route path="/analytics/view-sessions" element={<AllViewSessionsPage />} />
                  <Route
                    path="/automations"
                    element={
                      <RequireAdminFeature feature="automation">
                        <AutomationsPage />
                      </RequireAdminFeature>
                    }
                  />
                  <Route path="/signatures" element={<SignatureRequestsPage />} />
                  <Route path="/signatures/:requestId" element={<SignatureRequestDetailPage />} />
                  <Route path="/settings" element={<UserSettingsPage />} />
                  <Route path="/settings/password" element={<PasswordSettingsPage />} />
                  <Route path="/settings/integrations" element={<IntegrationsSettingsPage />} />
                  <Route
                    path="/settings/api-keys"
                    element={
                      <RequireAdminFeature feature="apiKeys">
                        <ApiKeysSettingsPage />
                      </RequireAdminFeature>
                    }
                  />
                  <Route path="/admin/settings" element={<RequireAuth adminOnly><AdminSettingsPage /></RequireAuth>} />
                  <Route path="/admin/branding" element={<RequireAuth adminOnly><AdminBrandingPage /></RequireAuth>} />
                  <Route path="/admin/users" element={<RequireAuth adminOnly><AdminUsersPage /></RequireAuth>} />
                  <Route path="/admin/roles" element={<RequireAuth adminOnly><AdminRolesPage /></RequireAuth>} />
                  <Route path="/admin/users/:userId" element={<RequireAuth adminOnly><AdminUserDetailPage /></RequireAuth>} />
                  <Route path="/admin/datarooms" element={<RequireAuth adminOnly><AdminDataroomsPage /></RequireAuth>} />
                  <Route path="/admin/login-activity" element={<RequireAuth adminOnly><AdminLoginActivityPage /></RequireAuth>} />
                  <Route path="/admin/security-alerts" element={<RequireAuth adminOnly><AdminSecurityAlertsPage /></RequireAuth>} />
                  <Route path="*" element={<NotFoundPage />} />
                </Route>
              </Routes>
            </Suspense>
          </UploadProvider>
          </UserProvider>
      </BrandingProvider>
      </TooltipProvider>
    </>
  );
}

export default App;
