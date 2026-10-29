import { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '../ui/Dialog';
import { Button } from '../ui/Button';
import { Input } from '../ui/Input';

export function TypedSignatureModal({ isOpen, onOpenChange, onSave, fieldType = 'signature', userName = '' }) {
  const { t } = useTranslation();
  const [text, setText] = useState('');
  const [selectedFont, setSelectedFont] = useState('DancingScript');

  useEffect(() => {
    if (isOpen && fieldType === 'full_name' && userName) {
      setText(userName);
    } else if (!isOpen) {
      setText('');
    }
  }, [isOpen, fieldType, userName]);

  const handleSave = () => {
    if (!text.trim()) return;
    onSave(text.trim());
    onOpenChange(false);
  };

  // Detect if text contains Arabic characters
  const hasArabic = /[\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF\uFB50-\uFDFF\uFE70-\uFEFF]/.test(text);
  const displayFont = hasArabic ? 'Amiri' : selectedFont;

  return (
    <Dialog open={isOpen} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-lg">
        <DialogHeader>
          <DialogTitle>
            {fieldType === 'signature' ? t('esign.signature.typeSignature') : 
             fieldType === 'initials' ? t('esign.signature.typeInitials') :
             fieldType === 'full_name' ? t('esign.signature.typeName') :
             t('esign.signature.typeText')}
          </DialogTitle>
        </DialogHeader>

        <div className="space-y-4 py-4">
          <div>
            <Input
              value={text}
              onChange={(e) => setText(e.target.value)}
              placeholder={
                fieldType === 'signature' ? t('esign.signature.enterYourName') :
                fieldType === 'initials' ? t('esign.signature.enterInitials') :
                fieldType === 'full_name' ? t('esign.signature.enterFullName') :
                t('esign.signature.enterText')
              }
              autoFocus
              className="text-lg"
            />
          </div>

          {(fieldType === 'signature' || fieldType === 'initials') && !hasArabic && (
            <div>
              <label className="block text-sm font-medium mb-2">
                {t('esign.signature.fontStyle')}
              </label>
              <select
                value={selectedFont}
                onChange={(e) => setSelectedFont(e.target.value)}
                className="w-full border rounded-md px-3 py-2"
              >
                <option value="DancingScript" style={{ fontFamily: 'Dancing Script, cursive' }}>
                  Dancing Script
                </option>
                <option value="cursive" style={{ fontFamily: 'cursive' }}>
                  Cursive
                </option>
                <option value="serif" style={{ fontFamily: 'serif' }}>
                  Serif
                </option>
              </select>
            </div>
          )}

          {/* Preview */}
          <div className="border-2 border-gray-300 rounded-lg p-6 bg-gray-50 min-h-[120px] flex items-center justify-center">
            {text ? (
              <div
                className="text-center"
                style={{
                  fontFamily: displayFont === 'DancingScript' ? 'Dancing Script, cursive' :
                             displayFont === 'Amiri' ? 'Amiri, serif' :
                             displayFont,
                  fontSize: fieldType === 'initials' ? '2rem' : '2.5rem',
                  direction: hasArabic ? 'rtl' : 'ltr'
                }}
              >
                {text}
              </div>
            ) : (
              <p className="text-gray-400">{t('esign.signature.previewAppears')}</p>
            )}
          </div>

          {hasArabic && (
            <p className="text-sm text-blue-600">
              {t('esign.signature.arabicDetected')}
            </p>
          )}
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            {t('common.cancel')}
          </Button>
          <Button onClick={handleSave} disabled={!text.trim()}>
            {t('common.save')}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
