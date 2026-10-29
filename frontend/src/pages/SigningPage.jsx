import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { Button } from '../components/ui/Button';
import { toast } from 'sonner';
import { getSigningData, requestOTP, verifyOTP, submitSignature, declineToSign } from '../services/esign';

export default function SigningPage() {
  const { token } = useParams();
  const { t } = useTranslation();
  const navigate = useNavigate();
  
  const [loading, setLoading] = useState(true);
  const [signingData, setSigningData] = useState(null);
  const [otpSent, setOtpSent] = useState(false);
  const [otpCode, setOtpCode] = useState('');
  const [otpVerified, setOtpVerified] = useState(false);
  const [fieldValues, setFieldValues] = useState({});
  const [showSignatureModal, setShowSignatureModal] = useState(false);
  const [showDeclineDialog, setShowDeclineDialog] = useState(false);
  const [declineReason, setDeclineReason] = useState('');
  const [currentField, setCurrentField] = useState(null);
  
  useEffect(() => {
    loadSigningData();
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
      setShowSignatureModal(true);
    } else {
      // For text fields, show input dialog
      const value = prompt(t('esign.field.enterValue'));
      if (value) {
        setFieldValues(prev => ({ ...prev, [field.id]: value }));
      }
    }
  };
  
  const handleSaveSignature = (signatureData) => {
    if (currentField) {
      setFieldValues(prev => ({ ...prev, [currentField.id]: signatureData }));
    }
    setShowSignatureModal(false);
    setCurrentField(null);
  };
  
  const handleSubmit = async () => {
    try {
      const fields = Object.entries(fieldValues).map(([field_id, value]) => ({
        field_id: parseInt(field_id),
        value
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
  
  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto"></div>
          <p className="mt-4 text-gray-600">{t('common.loading')}</p>
        </div>
      </div>
    );
  }
  
  if (!signingData) {
    return <div className="container mx-auto p-4">{t('esign.error.notFound')}</div>;
  }
  
  const { signature_request, signer, fields, can_sign, can_sign_reason } = signingData;
  
  return (
    <div className="min-h-screen bg-gray-50 py-8">
      <div className="container mx-auto max-w-4xl px-4">
        {/* Header */}
        <div className="bg-white rounded-lg shadow p-6 mb-6">
          <h1 className="text-2xl font-bold mb-2">{signature_request.title}</h1>
          {signature_request.message && (
            <p className="text-gray-600 mb-4">{signature_request.message}</p>
          )}
          
          {/* OTP Verification Section */}
          {!otpVerified && (
            <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4 mb-4">
              <h3 className="font-semibold mb-2">{t('esign.otp.verificationRequired')}</h3>
              {!otpSent ? (
                <Button onClick={handleRequestOTP}>
                  {t('esign.otp.request')}
                </Button>
              ) : (
                <div className="flex gap-2">
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
          
          {otpVerified && can_sign && (
            <div className="bg-green-50 border border-green-200 rounded-lg p-4 mb-4">
              <p className="text-green-800">{t('esign.readyToSign')}</p>
            </div>
          )}
          
          {!can_sign && (
            <div className="bg-red-50 border border-red-200 rounded-lg p-4 mb-4">
              <p className="text-red-800">{can_sign_reason}</p>
            </div>
          )}
        </div>
        
        {/* Document Preview Placeholder */}
        <div className="bg-white rounded-lg shadow p-6 mb-6">
          <h2 className="text-lg font-semibold mb-4">{t('esign.document.preview')}</h2>
          <div className="bg-gray-100 border-2 border-dashed border-gray-300 rounded-lg p-8 text-center">
            <p className="text-gray-500">{t('esign.document.pdfViewerPlaceholder')}</p>
            <p className="text-sm text-gray-400 mt-2">
              {signature_request.document.name} ({signature_request.document.num_pages} {t('common.pages')})
            </p>
          </div>
          
          {/* Fields to sign */}
          <div className="mt-6">
            <h3 className="font-semibold mb-3">{t('esign.fields.toSign')}</h3>
            <div className="space-y-2">
              {fields?.map(field => (
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
        </div>
        
        {/* Actions */}
        <div className="bg-white rounded-lg shadow p-6">
          <div className="flex gap-3 justify-end">
            <Button
              variant="outline"
              onClick={() => setShowDeclineDialog(true)}
            >
              {t('esign.action.decline')}
            </Button>
            <Button
              onClick={handleSubmit}
              disabled={!can_sign || Object.keys(fieldValues).length < (fields?.filter(f => f.required).length || 0)}
            >
              {t('esign.action.submit')}
            </Button>
          </div>
        </div>
        
        {/* Simple Signature Modal */}
        {showSignatureModal && (
          <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
            <div className="bg-white rounded-lg p-6 max-w-lg w-full">
              <h3 className="text-lg font-semibold mb-4">{t('esign.signature.draw')}</h3>
              <div className="border-2 border-gray-300 rounded h-48 mb-4 bg-white">
                <p className="text-center pt-20 text-gray-400">{t('esign.signature.canvasPlaceholder')}</p>
              </div>
              <div className="flex gap-2 justify-end">
                <Button variant="outline" onClick={() => setShowSignatureModal(false)}>
                  {t('common.cancel')}
                </Button>
                <Button onClick={() => handleSaveSignature('signature-placeholder-data')}>
                  {t('common.save')}
                </Button>
              </div>
            </div>
          </div>
        )}
        
        {/* Decline Dialog */}
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
                <Button onClick={handleDecline}>
                  {t('esign.action.confirmDecline')}
                </Button>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
