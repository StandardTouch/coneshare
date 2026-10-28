import { Link } from 'react-router-dom';
import { useBranding } from '../contexts/BrandingProvider';
import { LanguagePicker } from '../components/common/LanguagePicker';

const LAST_UPDATED = 'October 27, 2026';

export function LegalDocumentPage({ title, children }) {
  const { brandName, brandLogoUrl, brandWebsiteUrl } = useBranding();

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
      <header className="border-b border-gray-200 bg-white dark:border-gray-800 dark:bg-gray-950">
        <div className="mx-auto flex max-w-3xl items-center justify-between gap-4 px-6 py-4">
          <Link to="/login" className="flex items-center gap-3">
            <img src={brandLogoUrl} alt="" className="h-8 w-auto" />
            <span className="font-semibold text-gray-900 dark:text-gray-50">{brandName}</span>
          </Link>
          <LanguagePicker />
        </div>
      </header>

      <main className="mx-auto max-w-3xl px-6 py-10 sm:py-14">
        <article className="prose prose-gray max-w-none dark:prose-invert prose-a:text-primary">
          <h1>{title}</h1>
          <p className="text-sm text-gray-500 dark:text-gray-400">
            <strong>Last updated:</strong> {LAST_UPDATED}
          </p>
          {children}
        </article>

        <footer className="mt-12 border-t border-gray-200 pt-8 text-sm text-gray-500 dark:border-gray-800 dark:text-gray-400">
          <p>
            <Link to="/login" className="text-primary hover:underline">
              Back to sign in
            </Link>
            {brandWebsiteUrl ? (
              <>
                {' · '}
                <a href={brandWebsiteUrl} className="text-primary hover:underline" target="_blank" rel="noopener noreferrer">
                  {brandWebsiteUrl.replace(/^https?:\/\//, '')}
                </a>
              </>
            ) : null}
          </p>
        </footer>
      </main>
    </div>
  );
}
