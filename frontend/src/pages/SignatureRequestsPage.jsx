import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { Button } from '../components/ui/Button';
import { toast } from 'sonner';
import { listSignatureRequests, cancelSignatureRequest, sendReminder } from '../services/esign';
import { STATUS_COLORS } from '../services/esign';

export default function SignatureRequestsPage() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  
  const [activeTab, setActiveTab] = useState('created');
  const [requests, setRequests] = useState([]);
  const [loading, setLoading] = useState(true);
  
  useEffect(() => {
    loadRequests();
  }, [activeTab]);
  
  const loadRequests = async () => {
    setLoading(true);
    try {
      const data = await listSignatureRequests(activeTab);
      setRequests(data);
    } catch (error) {
      toast.error(t('esign.error.loadFailed'));
    } finally {
      setLoading(false);
    }
  };
  
  const handleCancel = async (requestId) => {
    if (!confirm(t('esign.request.confirmCancel'))) return;
    
    try {
      await cancelSignatureRequest(requestId);
      toast.success(t('esign.success.cancelled'));
      loadRequests();
    } catch (error) {
      toast.error(t('esign.error.cancelFailed'));
    }
  };
  
  const handleRemind = async (requestId) => {
    try {
      await sendReminder(requestId);
      toast.success(t('esign.success.reminderSent'));
    } catch (error) {
      toast.error(t('esign.error.reminderFailed'));
    }
  };
  
  return (
    <div className="container mx-auto py-8 px-4">
      {/* Header */}
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-3xl font-bold">{t('esign.title')}</h1>
        <Button onClick={() => navigate('/documents')}>
          {t('esign.request.createNew')}
        </Button>
      </div>
      
      {/* Tabs */}
      <div className="border-b border-gray-200 mb-6">
        <nav className="-mb-px flex gap-8">
          <button
            onClick={() => setActiveTab('created')}
            className={`py-4 px-1 border-b-2 font-medium text-sm ${
              activeTab === 'created'
                ? 'border-blue-500 text-blue-600'
                : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
            }`}
          >
            {t('esign.tabs.sentByMe')}
          </button>
          <button
            onClick={() => setActiveTab('awaiting')}
            className={`py-4 px-1 border-b-2 font-medium text-sm ${
              activeTab === 'awaiting'
                ? 'border-blue-500 text-blue-600'
                : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
            }`}
          >
            {t('esign.tabs.awaitingMySignature')}
          </button>
        </nav>
      </div>
      
      {/* Requests List */}
      {loading ? (
        <div className="text-center py-12">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto"></div>
          <p className="mt-4 text-gray-600">{t('common.loading')}</p>
        </div>
      ) : requests.length === 0 ? (
        <div className="text-center py-12 bg-gray-50 rounded-lg">
          <p className="text-gray-500">{t('esign.request.noRequests')}</p>
        </div>
      ) : (
        <div className="space-y-4">
          {requests.map(request => (
            <div key={request.id} className="bg-white border rounded-lg p-4 hover:shadow-md transition-shadow">
              <div className="flex justify-between items-start">
                <div className="flex-1">
                  <div className="flex items-center gap-3 mb-2">
                    <h3 className="text-lg font-semibold">{request.title}</h3>
                    <span className={`px-2 py-1 rounded text-xs font-medium ${STATUS_COLORS[request.status]}`}>
                      {t(`esign.status.${request.status}`)}
                    </span>
                  </div>
                  
                  <p className="text-sm text-gray-600 mb-2">
                    {t('esign.request.document')}: {request.document_name}
                  </p>
                  
                  {activeTab === 'created' && (
                    <div className="text-sm text-gray-500">
                      {request.signers_count} {t('esign.request.signers')} • 
                      {request.signed_count} {t('esign.request.signed')}
                    </div>
                  )}
                  
                  {activeTab === 'awaiting' && request.signer_status && (
                    <div className="text-sm">
                      <span className="text-gray-500">{t('esign.request.yourStatus')}:</span>
                      <span className={`ml-2 px-2 py-1 rounded text-xs ${STATUS_COLORS[request.signer_status]}`}>
                        {t(`esign.signerStatus.${request.signer_status}`)}
                      </span>
                    </div>
                  )}
                  
                  <p className="text-xs text-gray-400 mt-2">
                    {t('esign.request.created')}: {new Date(request.created_at).toLocaleDateString()}
                  </p>
                </div>
                
                <div className="flex gap-2">
                  {activeTab === 'awaiting' && request.signer_token && (
                    <Button
                      size="sm"
                      onClick={() => navigate(`/sign/${request.signer_token}`)}
                    >
                      {t('esign.action.viewSign')}
                    </Button>
                  )}
                  
                  {activeTab === 'created' && (
                    <>
                      {request.status === 'completed' && (
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={() => navigate(`/documents/${request.document_id}`)}
                        >
                          {t('esign.action.viewDocument')}
                        </Button>
                      )}
                      
                      {['sent', 'in_progress'].includes(request.status) && (
                        <>
                          <Button
                            size="sm"
                            variant="outline"
                            onClick={() => handleRemind(request.id)}
                          >
                            {t('esign.action.sendReminder')}
                          </Button>
                          <Button
                            size="sm"
                            variant="outline"
                            onClick={() => handleCancel(request.id)}
                          >
                            {t('esign.action.cancel')}
                          </Button>
                        </>
                      )}
                    </>
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
