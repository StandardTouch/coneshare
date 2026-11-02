import { useState, useEffect, useMemo, useRef } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { Button } from '../components/ui/Button';
import { toast } from 'sonner';
import {
  getSigningData,
  requestOTP,
  verifyOTP,
  submitSignature,
  declineToSign,
  getSignerDocumentPdfUrl,
  downloadSignerSourcePdf,
} from '../services/esign';
import { SignatureDrawModal } from '../components/esign/SignatureDrawModal';
import { TypedSignatureModal } from '../components/esign/TypedSignatureModal';
import { EsignPdfViewer } from '../components/esign/EsignPdfViewer';
import { useUser } from '../contexts/UserProvider';

export default function SigningPage() {
  const { token } = useParams();
  const { t } = useTranslation();
  const navigate = useNavigate();
  const { user } = useUser();
  const viewerRef = useRef(null);

  const [loading, setLoading] = useState(true);
  const [signingData, setSigningData] = useState(null);
  const [otpSent, setOtpSent] = useState(false);
  const [otpCode, setOtpCode] = useState('');
  const [otpVerified, setOtpVerified] = useState(false);
  const [fieldValues, setFieldValues] = useState({});
  const [showDrawModal, setShowDrawModal] = useState(false);
  const [showTypeModal, setShowTypeModal] = useState(false);
  const [showDeclineDialog, setShowDeclineDialog] = useState(false);
  const [declineReason, setDeclineReason] = useState('');
  const [currentField, setCurrentField] = useState(null);
  const [scrollToFieldId, setScrollToFieldId] = useState(null);

  useEffect(() => {
    loadSigningData();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token]);

  const loadSigningData = async () => {
    try {
      const data = await getSigningData(token);
      setSigningData(data);
      setOtpVerified(!!data.otp_verified_at);
    } catch (error) {
      toast.error(t('esign.error.loadFailed'));
      navigate('/');
    } finally {
      setLoading(false);
    }
  };

  const handleRequestOTP = async () => {
    try {
      await requestOTP(token);
      setOtpSent(true);
      toast.success(t('esign.otp.sent'));
    } catch (error) {
      toast.error(t('esign.otp.sendFailed'));
    }
  };

  const handleVerifyOTP = async () => {
    try {
      await verifyOTP(token, otpCode);
      setOtpVerified(true);
      toast.success(t('esign.otp.verified'));
    } catch (error) {
      toast.error(t('esign.otp.verifyFailed'));
    }
  };

  const handleFieldClick = (field) => {
    if (!otpVerified) {
      toast.error(t('esign.error.otpRequired'));
      return;
    }
    setCurrentField(field);
    if (field.field_type === 'signature' || field.field_type === 'initials') {
      setShowDrawModal(true);
    } else if (field.field_type === 'full_name' || field.field_type === 'text') {
      setShowTypeModal(true);
    } else if (field.field_type === 'date_signed') {
      const today = new Date().toLocaleDateString();
      setFieldValues((prev) => ({ ...prev, [field.id]: today }));
    }
  };

  const handleSaveDrawnSignature = (signatureData) => {
    if (currentField) {
      setFieldValues((prev) => ({ ...prev, [currentField.id]: signatureData }));
    }
    setShowDrawModal(false);
    setCurrentField(null);
  };

  const handleSaveTypedSignature = (text) => {
    if (currentField) {
      setFieldValues((prev) => ({ ...prev, [currentField.id]: text }));
    }
    setShowTypeModal(false);
    setCurrentField(null);
  };

  const handleSubmit = async () => {
    try {
      const fields = Object.entries(fieldValues).map(([field_id, value]) => ({
        field_id,
        value,
      }));

      await submitSignature(token, fields);
      toast.success(t('esign.success.signed'));
      navigate('/signatures');
    } catch (error) {
      toast.error(t('esign.error.submitFailed'));
    }
  };

  const handleDecline = async () => {
    try {
      await declineToSign(token, declineReason);
      toast.success(t('esign.success.declined'));
      navigate('/signatures');
    } catch (error) {
      toast.error(t('esign.error.declineFailed'));
    }
  };

  const handleDownload = async () => {
    try {
      const name = signingData?.signature_request?.document?.name || 'document.pdf';
      await downloadSignerSourcePdf(token, name);
    } catch (error) {
      toast.error(t('esign.document.downloadFailed'));
    }
  };

  const filledFieldIds = useMemo(() => new Set(Object.keys(fieldValues)), [fieldValues]);

  useEffect(() => {
    if (!otpVerified || !signingData?.fields?.length) return;
    const firstUnsigned = signingData.fields.find(
      (f) => f.required && !fieldValues[f.id]
    );
    if (firstUnsigned) {
      setScrollToFieldId(firstUnsigned.id);
    }
  }, [otpVerified, signingData, fieldValues]);

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto" />
          <p className="mt-4 text-gray-600">{t('common.loading')}</p>
        </div>
      </div>
    );
  }

  if (!signingData) {
    return <div className="container mx-auto p-4">{t('esign.error.notFound')}</div>;
  }

  const { signature_request, fields, all_fields, can_sign, can_sign_reason, id: signerRecordId } =
    signingData;
  const overlayFields = all_fields || fields;
  const pdfUrl = otpVerified ? getSignerDocumentPdfUrl(token) : null;

  return (
    <div className="min-h-screen bg-gray-50 py-6">
      <div className="container mx-auto max-w-6xl px-4">
        <div className="bg-white rounded-lg shadow p-6 mb-4">
          <h1 className="text-2xl font-bold mb-2">{signature_request.title}</h1>
          {signature_request.message && (
            <p className="text-gray-600 mb-4">{signature_request.message}</p>
          )}

          {!otpVerified && (
            <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4 mb-4">
              <h3 className="font-semibold mb-2">{t('esign.otp.verificationRequired')}</h3>
              {!otpSent ? (
                <Button onClick={handleRequestOTP}>{t('esign.otp.request')}</Button>
              ) : (
                <div className="flex flex-wrap gap-2">
                  <input
                    type="text"
                    value={otpCode}
                    onChange={(e) => setOtpCode(e.target.value)}
                    placeholder={t('esign.otp.enterCode')}
                    maxLength={6}
                    className="border rounded px-3 py-2 w-32"
                  />
                  <Button onClick={handleVerifyOTP} disabled={otpCode.length !== 6}>
                    {t('esign.otp.verify')}
                  </Button>
                  <Button variant="outline" onClick={handleRequestOTP}>
                    {t('esign.otp.resend')}
                  </Button>
                </div>
              )}
            </div>
          )}

          {otpVerified && (
            <div className="flex flex-wrap items-center gap-3 mb-2">
              <div className="bg-green-50 border border-green-200 rounded-lg px-4 py-2 text-green-800">
                {can_sign ? t('esign.readyToSign') : can_sign_reason}
              </div>
              <Button variant="outline" size="sm" onClick={handleDownload}>
                {t('esign.document.downloadOriginal')}
              </Button>
            </div>
          )}
        </div>

        {otpVerified && (
          <div className="bg-white rounded-lg shadow mb-4 overflow-hidden h-[min(75vh,900px)] flex flex-col">
            <h2 className="text-lg font-semibold px-4 py-3 border-b shrink-0">
              {t('esign.document.preview')}
            </h2>
            <div className="flex-1 min-h-0">
              <EsignPdfViewer
                ref={viewerRef}
                pdfUrl={pdfUrl}
                mode="signing"
                fields={overlayFields}
                currentUserSignerId={signerRecordId}
                filledFieldIds={filledFieldIds}
                onFieldClick={handleFieldClick}
                scrollToFieldId={scrollToFieldId}
                showThumbnails
                showPageControls
              />
            </div>
          </div>
        )}

        <div className="bg-white rounded-lg shadow p-6 mb-4">
          <h3 className="font-semibold mb-3">{t('esign.fields.toSign')}</h3>
          <div className="space-y-2">
            {fields?.map((field) => (
              <div
                key={field.id}
                className={`border rounded-lg p-3 cursor-pointer hover:bg-gray-50 ${
                  fieldValues[field.id] ? 'bg-green-50 border-green-300' : 'border-gray-200'
                }`}
                onClick={() => handleFieldClick(field)}
              >
                <div className="flex justify-between items-center">
                  <span className="font-medium">
                    {t(`esign.fieldType.${field.field_type}`)}
                    {field.required && <span className="text-red-500 ml-1">*</span>}
                    <span className="text-gray-400 text-sm ml-2">
                      {t('common.page')} {field.page_number}
                    </span>
                  </span>
                  {fieldValues[field.id] ? (
                    <span className="text-green-600">✓ {t('esign.field.filled')}</span>
                  ) : (
                    <span className="text-blue-600">{t('esign.field.clickToFill')}</span>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>

        <div className="bg-white rounded-lg shadow p-6">
          <div className="flex gap-3 justify-end">
            <Button variant="outline" onClick={() => setShowDeclineDialog(true)}>
              {t('esign.action.decline')}
            </Button>
            <Button
              onClick={handleSubmit}
              disabled={
                !can_sign ||
                Object.keys(fieldValues).length < (fields?.filter((f) => f.required).length || 0)
              }
            >
              {t('esign.action.submit')}
            </Button>
          </div>
        </div>

        <SignatureDrawModal
          isOpen={showDrawModal}
          onOpenChange={setShowDrawModal}
          onSave={handleSaveDrawnSignature}
          fieldType={currentField?.field_type}
        />

        <TypedSignatureModal
          isOpen={showTypeModal}
          onOpenChange={setShowTypeModal}
          onSave={handleSaveTypedSignature}
          fieldType={currentField?.field_type}
          userName={user?.name}
        />

        {showDeclineDialog && (
          <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
            <div className="bg-white rounded-lg p-6 max-w-md w-full">
              <h3 className="text-lg font-semibold mb-4">{t('esign.decline.title')}</h3>
              <textarea
                value={declineReason}
                onChange={(e) => setDeclineReason(e.target.value)}
                placeholder={t('esign.decline.reasonPlaceholder')}
                className="w-full border rounded p-2 mb-4"
                rows={4}
              />
              <div className="flex gap-2 justify-end">
                <Button variant="outline" onClick={() => setShowDeclineDialog(false)}>
                  {t('common.cancel')}
                </Button>
                <Button onClick={handleDecline}>{t('esign.action.confirmDecline')}</Button>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
