import { useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { useBranding } from '../contexts/BrandingProvider';
import { BRAND_CONFIG } from '../lib/brandConfig';
import { PrivacyPolicyContent } from '../content/legal/privacyPolicyEn';
import { LegalDocumentPage } from './LegalDocumentPage';

export function PrivacyPage() {
  const { t } = useTranslation();
  const { brandName } = useBranding();

  useEffect(() => {
    document.title = `${t('auth.privacy')} - ${brandName}`;
  }, [brandName, t]);

  return (
    <LegalDocumentPage title={t('auth.privacy', { defaultValue: 'Privacy Policy' })}>
      <PrivacyPolicyContent
        operatorName={brandName}
        contactEmail={BRAND_CONFIG.contactEmail}
      />
    </LegalDocumentPage>
  );
}
