import { useEffect, useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { toast } from 'sonner';
import { Loader2 } from 'lucide-react';

import { useBranding } from '../contexts/BrandingProvider';
import { Button } from '../components/ui/Button';
import { Input } from '../components/ui/Input';
import { LanguagePicker } from '../components/common/LanguagePicker';
import { extractApiErrorMessage } from '../lib/apiErrors';
import * as api from '../services/api';

export function SetPasswordPage() {
  const { uid, token } = useParams();
  const navigate = useNavigate();
  const { t } = useTranslation();
  const { brandName, brandLogoUrl, brandWebsiteUrl, termsUrl, privacyPolicyUrl } = useBranding();

  const [phase, setPhase] = useState('validating');
  const [email, setEmail] = useState('');
  const [password1, setPassword1] = useState('');
  const [password2, setPassword2] = useState('');
  const [error, setError] = useState(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  useEffect(() => {
    document.title = `${t('auth.setPasswordTitle')} - ${brandName}`;
  }, [brandName, t]);

  const inviteErrorMessage = (payload) => {
    const code = payload?.code;
    if (code === 'used') return t('auth.inviteLinkUsed');
    if (code === 'expired') return t('auth.inviteLinkExpired');
    if (typeof payload?.detail === 'string' && payload.detail.trim()) return payload.detail;
    return t('auth.inviteLinkInvalid');
  };

  useEffect(() => {
    let mounted = true;

    const validate = async () => {
      if (!uid || !token) {
        if (mounted) {
          setPhase('invalid');
          setError(t('auth.inviteLinkInvalid'));
        }
        return;
      }
      try {
        const data = await api.validateInviteToken({ uid, token });
        if (!mounted) return;
        if (data?.valid) {
          setEmail(data.email || '');
          setPhase('ready');
        } else {
          setPhase('invalid');
          setError(inviteErrorMessage(data));
        }
      } catch (err) {
        if (!mounted) return;
        setPhase('invalid');
        const payload = err?.response?.data;
        setError(payload ? inviteErrorMessage(payload) : extractApiErrorMessage(err, t('auth.inviteLinkInvalid')));
      }
    };

    validate();
    return () => {
      mounted = false;
    };
  }, [uid, token, t]);

  const handleSubmit = async (event) => {
    event.preventDefault();
    setIsSubmitting(true);
    setError(null);
    try {
      await api.completeInviteSetPassword({
        uid,
        token,
        password1,
        password2,
      });
      toast.success(t('auth.setPasswordSuccess'));
      navigate('/login', { state: { invitePasswordSet: true } });
    } catch (err) {
      setError(extractApiErrorMessage(err, t('auth.setPasswordFailed')));
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="flex min-h-screen flex-col items-center justify-center bg-gray-50 py-12 px-4 sm:px-6 lg:px-8 dark:bg-gray-900">
      <div className="absolute top-4 right-4">
        <LanguagePicker />
      </div>
      <div className="w-full max-w-md space-y-8">
        <div className="flex flex-col items-center">
          {brandLogoUrl ? (
            <div className="mb-4 flex h-16 w-16 items-center justify-center rounded-full bg-white p-2 shadow-sm border border-gray-100 dark:bg-gray-800 dark:border-gray-700">
              <img src={brandLogoUrl} alt={`${brandName} logo`} className="h-12 w-12 object-contain" />
            </div>
          ) : null}
          <h2 className="text-center text-3xl font-extrabold text-gray-900 dark:text-white">
            {t('auth.setPasswordTitle')}
          </h2>
          <p className="mt-2 text-center text-sm text-gray-600 dark:text-gray-400">
            {t('auth.setPasswordSubtitle', { brandName })}
          </p>
        </div>

        {phase === 'validating' && (
          <div className="flex justify-center py-8">
            <Loader2 className="h-8 w-8 animate-spin text-indigo-600" />
          </div>
        )}

        {phase === 'invalid' && (
          <div className="rounded-md bg-white p-6 shadow dark:bg-gray-800">
            <p className="text-sm text-red-600 dark:text-red-400">{error}</p>
            <p className="mt-4 text-sm">
              <Link className="font-medium text-indigo-600 hover:text-indigo-500" to="/login">
                {t('auth.backToSignIn')}
              </Link>
            </p>
          </div>
        )}

        {phase === 'ready' && (
          <form onSubmit={handleSubmit} className="mt-8 space-y-6">
            {email ? (
              <p className="text-center text-sm text-gray-600 dark:text-gray-400">
                {t('auth.setPasswordForEmail', { email })}
              </p>
            ) : null}
            <div className="space-y-4 rounded-md shadow-sm">
              <div>
                <label htmlFor="password1" className="sr-only">
                  {t('settings.newPassword')}
                </label>
                <Input
                  id="password1"
                  name="password1"
                  type="password"
                  autoComplete="new-password"
                  required
                  placeholder={t('settings.newPassword')}
                  value={password1}
                  onChange={(e) => setPassword1(e.target.value)}
                  disabled={isSubmitting}
                />
              </div>
              <div>
                <label htmlFor="password2" className="sr-only">
                  {t('settings.confirmPassword')}
                </label>
                <Input
                  id="password2"
                  name="password2"
                  type="password"
                  autoComplete="new-password"
                  required
                  placeholder={t('settings.confirmPassword')}
                  value={password2}
                  onChange={(e) => setPassword2(e.target.value)}
                  disabled={isSubmitting}
                />
              </div>
            </div>
            {error ? <p className="text-sm text-red-600 dark:text-red-400">{error}</p> : null}
            <Button type="submit" className="w-full" disabled={isSubmitting}>
              {isSubmitting ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  {t('auth.settingPassword')}
                </>
              ) : (
                t('auth.setPasswordSubmit')
              )}
            </Button>
          </form>
        )}

        <div className="mt-8 flex flex-col items-center justify-center gap-2 text-xs text-gray-400">
          <div className="flex items-center gap-3">
            {brandWebsiteUrl ? (
              <>
                <a
                  href={brandWebsiteUrl}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="hover:text-gray-600 transition-colors"
                >
                  {t('auth.aboutBrand', { brandName })}
                </a>
                <span className="text-gray-300">&bull;</span>
              </>
            ) : null}
            {termsUrl ? (
              <>
                <Link to="/terms" className="hover:text-gray-600 transition-colors">
                  {t('legal.terms')}
                </Link>
                <span className="text-gray-300">&bull;</span>
              </>
            ) : null}
            {privacyPolicyUrl ? (
              <Link to="/privacy" className="hover:text-gray-600 transition-colors">
                {t('legal.privacy')}
              </Link>
            ) : null}
          </div>
        </div>
      </div>
    </div>
  );
}

export default SetPasswordPage;
