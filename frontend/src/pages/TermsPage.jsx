import { useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { useBranding } from '../contexts/BrandingProvider';
import { BRAND_CONFIG } from '../lib/brandConfig';
import { TermsOfServiceContent } from '../content/legal/termsOfServiceEn';
import { LegalDocumentPage } from './LegalDocumentPage';

export function TermsPage() {
  const { t } = useTranslation();
  const { brandName } = useBranding();

  useEffect(() => {
    document.title = `${t('auth.terms')} - ${brandName}`;
  }, [brandName, t]);

  return (
    <LegalDocumentPage title={t('auth.terms', { defaultValue: 'Terms of Service' })}>
      <TermsOfServiceContent
        operatorName={brandName}
        contactEmail={BRAND_CONFIG.contactEmail}
      />
    </LegalDocumentPage>
  );
}
