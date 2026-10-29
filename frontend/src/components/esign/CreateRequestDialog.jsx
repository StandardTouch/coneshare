import { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { useNavigate } from 'react-router-dom';
import { Loader2, X, Plus, Users } from 'lucide-react';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '../ui/Dialog';
import { Button } from '../ui/Button';
import { Input } from '../ui/Input';
import { Label } from '../ui/Label';
import { toast } from 'sonner';
import { createSignatureRequest, updateSignatureFields } from '../../services/esign';
import { FieldPlacementEditor } from './FieldPlacementEditor';

export function CreateRequestDialog({ isOpen, onOpenChange, document, users }) {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const [step, setStep] = useState(1);
  const [title, setTitle] = useState('');
  const [message, setMessage] = useState('');
  const [signers, setSigners] = useState([]);
  const [signingOrder, setSigningOrder] = useState(false);
  const [expiresInDays, setExpiresInDays] = useState(7);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [requestId, setRequestId] = useState(null);

  useEffect(() => {
    if (!isOpen) {
      setStep(1);
      setTitle('');
      setMessage('');
      setSigners([]);
      setSigningOrder(false);
      setExpiresInDays(7);
      setRequestId(null);
    } else if (document) {
      setTitle(`Sign ${document.name}`);
    }
  }, [isOpen, document]);

  const handleAddSigner = () => {
    setSigners([...signers, { user_id: '', signing_order: signers.length + 1 }]);
  };

  const handleRemoveSigner = (index) => {
    setSigners(signers.filter((_, i) => i !== index));
  };

  const handleSignerChange = (index, userId) => {
    const updated = [...signers];
    updated[index] = { ...updated[index], user_id: parseInt(userId) };
    setSigners(updated);
  };

  const handleNext = async () => {
    if (step === 1) {
      if (!title.trim()) {
        toast.error(t('esign.create.titleRequired'));
        return;
      }
      if (signers.length === 0) {
        toast.error(t('esign.create.signersRequired'));
        return;
      }
      if (signers.some(s => !s.user_id)) {
        toast.error(t('esign.create.selectAllSigners'));
        return;
      }

      setIsSubmitting(true);
      try {
        const expiresAt = new Date();
        expiresAt.setDate(expiresAt.getDate() + expiresInDays);

        const data = {
          document_id: document.id,
          title,
          message,
          signers: signers.map((s, idx) => ({
            user_id: s.user_id,
            signing_order: signingOrder ? idx + 1 : 1
          })),
          signing_order: signingOrder,
          expires_at: expiresAt.toISOString()
        };

        const request = await createSignatureRequest(data);
        setRequestId(request.id);
        setStep(2);
      } catch (error) {
        toast.error(t('esign.error.createFailed'));
      } finally {
        setIsSubmitting(false);
      }
    }
  };

  const handleFieldsSaved = async (fields) => {
    setIsSubmitting(true);
    try {
      await updateSignatureFields(requestId, fields);
      toast.success(t('esign.create.requestCreated'));
      onOpenChange(false);
      navigate('/signatures');
    } catch (error) {
      toast.error(t('esign.error.fieldsSaveFailed'));
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <Dialog open={isOpen} onOpenChange={!isSubmitting ? onOpenChange : undefined}>
      <DialogContent className="sm:max-w-4xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>
            {step === 1 ? t('esign.create.title') : t('esign.create.placeFields')}
          </DialogTitle>
        </DialogHeader>

        {step === 1 ? (
          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label htmlFor="title">{t('esign.create.requestTitle')}</Label>
              <Input
                id="title"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                placeholder={t('esign.create.titlePlaceholder')}
                disabled={isSubmitting}
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="message">{t('esign.create.message')}</Label>
              <textarea
                id="message"
                value={message}
                onChange={(e) => setMessage(e.target.value)}
                placeholder={t('esign.create.messagePlaceholder')}
                className="w-full border rounded-md px-3 py-2"
                rows={3}
                disabled={isSubmitting}
              />
            </div>

            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <Label>{t('esign.create.signers')}</Label>
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={handleAddSigner}
                  disabled={isSubmitting}
                >
                  <Plus className="h-4 w-4 mr-1" />
                  {t('esign.create.addSigner')}
                </Button>
              </div>
              
              {signers.length === 0 ? (
                <div className="text-center py-8 text-gray-500 border-2 border-dashed rounded-lg">
                  <Users className="h-12 w-12 mx-auto mb-2 opacity-50" />
                  <p>{t('esign.create.noSigners')}</p>
                </div>
              ) : (
                <div className="space-y-2">
                  {signers.map((signer, index) => (
                    <div key={index} className="flex gap-2 items-center">
                      {signingOrder && (
                        <span className="text-sm font-medium w-8">{index + 1}.</span>
                      )}
                      <select
                        value={signer.user_id}
                        onChange={(e) => handleSignerChange(index, e.target.value)}
                        className="flex-1 border rounded-md px-3 py-2"
                        disabled={isSubmitting}
                      >
                        <option value="">{t('esign.create.selectUser')}</option>
                        {users?.map(user => (
                          <option key={user.id} value={user.id}>
                            {user.name} ({user.email})
                          </option>
                        ))}
                      </select>
                      <Button
                        type="button"
                        variant="ghost"
                        size="sm"
                        onClick={() => handleRemoveSigner(index)}
                        disabled={isSubmitting}
                      >
                        <X className="h-4 w-4" />
                      </Button>
                    </div>
                  ))}
                </div>
              )}
            </div>

            <div className="space-y-2">
              <Label>{t('esign.create.signingOrder')}</Label>
              <div className="space-y-2">
                <label className="flex items-center space-x-2">
                  <input
                    type="radio"
                    checked={!signingOrder}
                    onChange={() => setSigningOrder(false)}
                    disabled={isSubmitting}
                  />
                  <span>{t('esign.create.parallel')}</span>
                  <span className="text-sm text-gray-500">
                    ({t('esign.create.parallelDesc')})
                  </span>
                </label>
                <label className="flex items-center space-x-2">
                  <input
                    type="radio"
                    checked={signingOrder}
                    onChange={() => setSigningOrder(true)}
                    disabled={isSubmitting}
                  />
                  <span>{t('esign.create.sequential')}</span>
                  <span className="text-sm text-gray-500">
                    ({t('esign.create.sequentialDesc')})
                  </span>
                </label>
              </div>
            </div>

            <div className="space-y-2">
              <Label htmlFor="expires">{t('esign.create.expiresIn')}</Label>
              <select
                id="expires"
                value={expiresInDays}
                onChange={(e) => setExpiresInDays(parseInt(e.target.value))}
                className="border rounded-md px-3 py-2"
                disabled={isSubmitting}
              >
                <option value={1}>1 {t('common.day')}</option>
                <option value={3}>3 {t('common.days')}</option>
                <option value={7}>7 {t('common.days')}</option>
                <option value={14}>14 {t('common.days')}</option>
                <option value={30}>30 {t('common.days')}</option>
              </select>
            </div>
          </div>
        ) : (
          <FieldPlacementEditor
            documentId={document?.id}
            signers={signers}
            users={users}
            onSave={handleFieldsSaved}
            onCancel={() => onOpenChange(false)}
          />
        )}

        {step === 1 && (
          <DialogFooter>
            <Button
              type="button"
              variant="outline"
              onClick={() => onOpenChange(false)}
              disabled={isSubmitting}
            >
              {t('common.cancel')}
            </Button>
            <Button onClick={handleNext} disabled={isSubmitting}>
              {isSubmitting ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  {t('common.creating')}
                </>
              ) : (
                t('common.next')
              )}
            </Button>
          </DialogFooter>
        )}
      </DialogContent>
    </Dialog>
  );
}
