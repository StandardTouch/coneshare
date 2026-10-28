import { useEffect } from 'react';
import { Link } from 'react-router-dom';
import { useBranding } from '../contexts/BrandingProvider';
import { BRAND_CONFIG } from '../lib/brandConfig';
import { LanguagePicker } from '../components/common/LanguagePicker';

/**
 * Public landing page for OAuth branding verification and unauthenticated visitors.
 * Set Google Cloud "Application home page" to: {SITE_DOMAIN}/welcome
 */
export function PublicAppHomePage() {
  const { brandName, brandLogoUrl, termsUrl, privacyPolicyUrl, brandWebsiteUrl } = useBranding();
  const contactEmail = BRAND_CONFIG.contactEmail;

  useEffect(() => {
    document.title = `${brandName} | Secure Document Sharing`;
  }, [brandName]);

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
      <header className="border-b border-gray-200 bg-white dark:border-gray-800 dark:bg-gray-950">
        <div className="mx-auto flex max-w-3xl items-center justify-between gap-4 px-6 py-4">
          <div className="flex items-center gap-3">
            <img src={brandLogoUrl} alt="" className="h-10 w-auto" />
            <span className="text-lg font-semibold text-gray-900 dark:text-gray-50">{brandName}</span>
          </div>
          <LanguagePicker />
        </div>
      </header>

      <main className="mx-auto max-w-3xl px-6 py-12 sm:py-16">
        <h1 className="text-3xl font-bold tracking-tight text-gray-900 dark:text-gray-50">
          Secure document sharing for {brandName}
        </h1>
        <p className="mt-4 text-lg text-gray-600 dark:text-gray-300">
          This application is operated by {brandName} for authorized staff and approved external
          recipients. It provides encrypted document storage, password-protected share links, virtual
          datarooms, file-request uploads, and optional import from Google Drive — all on infrastructure
          controlled by {brandName}.
        </p>

        <ul className="mt-6 list-disc space-y-2 pl-6 text-gray-700 dark:text-gray-300">
          <li>Staff sign in with organization-issued accounts.</li>
          <li>External parties access documents only via links or upload forms your team sends.</li>
          <li>
            Connecting Google Drive (optional) imports files you select; see our Privacy Policy for how
            Google user data is handled.
          </li>
        </ul>

        <div className="mt-10 flex flex-wrap gap-4">
          <Link
            to="/login"
            className="inline-flex items-center rounded-lg bg-[#0D7C75] px-5 py-2.5 text-sm font-medium text-white hover:bg-[#0D7C75]/90"
          >
            Staff sign in
          </Link>
          {brandWebsiteUrl ? (
            <a
              href={brandWebsiteUrl}
              className="inline-flex items-center rounded-lg border border-gray-300 px-5 py-2.5 text-sm font-medium text-gray-800 hover:bg-gray-100 dark:border-gray-600 dark:text-gray-100 dark:hover:bg-gray-800"
              target="_blank"
              rel="noopener noreferrer"
            >
              Main clinic website
            </a>
          ) : null}
        </div>

        <section className="mt-12 border-t border-gray-200 pt-8 dark:border-gray-800">
          <h2 className="text-sm font-semibold uppercase tracking-wide text-gray-500">Legal &amp; support</h2>
          <p className="mt-3 text-gray-700 dark:text-gray-300">
            <a href={termsUrl} className="text-[#0D7C75] underline">
              Terms of Service
            </a>
            {' · '}
            <a href={privacyPolicyUrl} className="text-[#0D7C75] underline">
              Privacy Policy
            </a>
          </p>
          <p className="mt-2 text-sm text-gray-600 dark:text-gray-400">
            Support:{' '}
            <a href={`mailto:${contactEmail}`} className="text-[#0D7C75] underline">
              {contactEmail}
            </a>
          </p>
        </section>
      </main>
    </div>
  );
}
