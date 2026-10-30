import { useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { useUser } from '../contexts/UserProvider';

/**
 * Syncs i18next language with the authenticated user's
 * language preference from the backend.
 */
export function useLanguageSync() {
  const { i18n } = useTranslation();
  const { user } = useUser();
  const changeLanguage = i18n.changeLanguage;

  useEffect(() => {
    const preferred = user?.language;
    if (!preferred || preferred === i18n.language) {
      return;
    }
    const supported = i18n.options.supportedLngs?.filter((code) => code !== 'cimode') ?? [];
    if (supported.includes(preferred)) {
      changeLanguage(preferred);
    }
  }, [user?.language, i18n.language, changeLanguage, i18n.options.supportedLngs]);
}
