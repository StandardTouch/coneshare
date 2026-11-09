import { useState, createElement } from 'react';
import { useTranslation } from 'react-i18next';
import { Button } from '../ui/Button';
import { Type, Edit, Calendar, User, FileText } from 'lucide-react';
import { getEsignDocumentPdfUrl } from '../../services/esign';
import { EsignPdfViewer } from './EsignPdfViewer';
import { clampFieldBox, defaultFieldSize, placeFieldAtClient } from './fieldPlacementUtils';

const FIELD_TYPES = [
  { type: 'signature', icon: Edit, label: 'Signature', color: 'bg-blue-100 border-blue-300' },
  { type: 'initials', icon: Edit, label: 'Initials', color: 'bg-green-100 border-green-300' },
  { type: 'date_signed', icon: Calendar, label: 'Date', color: 'bg-purple-100 border-purple-300' },
  { type: 'full_name', icon: User, label: 'Name', color: 'bg-orange-100 border-orange-300' },
  { type: 'text', icon: FileText, label: 'Text', color: 'bg-gray-100 border-gray-300' },
];

export function FieldPlacementEditor({ documentId, signers, users, onSave, onCancel }) {
  const { t } = useTranslation();
  const [fields, setFields] = useState([]);
  const [draggedField, setDraggedField] = useState(null);
  const [selectedSignerIndex, setSelectedSignerIndex] = useState(0);

  const pdfUrl = documentId ? getEsignDocumentPdfUrl(documentId) : null;
  const activeSigner = signers[selectedSignerIndex];

  const handlePageDrop = (e, pageNumber) => {
    if (!draggedField || !activeSigner?.id) return;

    const pageEl = e.currentTarget;
    const rect = pageEl.getBoundingClientRect();
    const size = defaultFieldSize(draggedField);
    const placed = placeFieldAtClient(rect, e.clientX, e.clientY, size);

    const newField = {
      id: `temp-${Date.now()}`,
      signer_id: activeSigner.id,
      field_type: draggedField,
      page_number: pageNumber,
      x: placed.x,
      y: placed.y,
      width: placed.width,
      height: placed.height,
      required: true,
    };

    setFields((prev) => [...prev, newField]);
    setDraggedField(null);
  };

  const handleFieldMove = (fieldId, patch) => {
    setFields((prev) => prev.map((field) => {
      if (field.id !== fieldId) return field;
      const next = { ...field, ...patch };
      return { ...next, ...clampFieldBox(next) };
    }));
  };

  const handleDeleteField = (fieldId) => {
    setFields((prev) => prev.filter((f) => f.id !== fieldId));
  };

  const handleSave = () => {
    if (fields.length === 0) {
      alert(t('esign.create.noFieldsPlaced'));
      return;
    }

    const apiFields = fields.map((f) => ({
      signer_id: f.signer_id,
      field_type: f.field_type,
      page_number: f.page_number,
      x: f.x,
      y: f.y,
      width: f.width,
      height: f.height,
      required: f.required,
    }));

    onSave(apiFields);
  };

  const getSignerLabel = (signer) => {
    if (signer.displayName) return signer.displayName;
    const user = users?.find((u) => u.id === signer.user_id);
    return user?.name || user?.email || t('esign.create.selectUser');
  };

  return (
    <div className="flex flex-col h-full min-h-[70vh]">
      <div className="border-b p-3 space-y-3 shrink-0">
        <div className="flex items-center justify-between flex-wrap gap-2">
          <div className="flex items-center gap-2">
            <label className="text-sm font-medium">{t('esign.create.selectSigner')}:</label>
            <select
              value={selectedSignerIndex}
              onChange={(e) => setSelectedSignerIndex(parseInt(e.target.value, 10))}
              className="border rounded px-2 py-1 text-sm"
            >
              {signers.map((signer, idx) => (
                <option key={signer.id ?? idx} value={idx}>
                  {getSignerLabel(signer)}
                </option>
              ))}
            </select>
          </div>
        </div>

        <div className="flex gap-2 flex-wrap">
          {FIELD_TYPES.map((fieldType) => (
            <div
              key={fieldType.type}
              draggable
              onDragStart={() => setDraggedField(fieldType.type)}
              className={`flex items-center gap-2 px-3 py-2 rounded border cursor-move ${fieldType.color} hover:shadow-md transition-shadow`}
            >
              {createElement(fieldType.icon, { className: 'h-4 w-4' })}
              <span className="text-sm font-medium">{fieldType.label}</span>
            </div>
          ))}
        </div>
        <p className="text-xs text-gray-500">{t('esign.create.dragInstruction')}</p>
      </div>

      <div className="flex-1 min-h-0">
        <EsignPdfViewer
          pdfUrl={pdfUrl}
          mode="placement"
          fields={fields}
          activeSignerId={activeSigner?.id}
          onPageDrop={handlePageDrop}
          onFieldMove={handleFieldMove}
          onFieldDelete={handleDeleteField}
          showThumbnails
          showPageControls
        />
      </div>

      <div className="border-t p-3 bg-gray-50 shrink-0">
        <div className="text-sm text-gray-600 mb-2">
          {t('esign.create.fieldsPlaced', { count: fields.length })}
        </div>
        {signers.map((signer, idx) => {
          const signerFields = fields.filter((f) => f.signer_id === signer.id);
          return (
            <div key={signer.id ?? idx} className="text-xs text-gray-500">
              {getSignerLabel(signer)}: {signerFields.length} {t('esign.create.fields')}
            </div>
          );
        })}
      </div>

      <div className="border-t p-3 flex justify-end gap-2 shrink-0">
        <Button variant="outline" onClick={onCancel}>
          {t('common.cancel')}
        </Button>
        <Button onClick={handleSave} disabled={fields.length === 0}>
          {t('esign.create.saveAndSend')}
        </Button>
      </div>
    </div>
  );
}
