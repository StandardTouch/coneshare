import { useState, useRef, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { Button } from '../ui/Button';
import { Loader2, Type, Edit, Calendar, User, FileText } from 'lucide-react';
import { getDocumentDownloadUrl } from '../../services/api';

const FIELD_TYPES = [
  { type: 'signature', icon: Edit, label: 'Signature', color: 'bg-blue-100 border-blue-300' },
  { type: 'initials', icon: Edit, label: 'Initials', color: 'bg-green-100 border-green-300' },
  { type: 'date_signed', icon: Calendar, label: 'Date', color: 'bg-purple-100 border-purple-300' },
  { type: 'full_name', icon: User, label: 'Name', color: 'bg-orange-100 border-orange-300' },
  { type: 'text', icon: FileText, label: 'Text', color: 'bg-gray-100 border-gray-300' }
];

export function FieldPlacementEditor({ documentId, signers, users, onSave, onCancel }) {
  const { t } = useTranslation();
  const [pdfUrl, setPdfUrl] = useState(null);
  const [numPages, setNumPages] = useState(0);
  const [currentPage, setCurrentPage] = useState(1);
  const [fields, setFields] = useState([]);
  const [draggedField, setDraggedField] = useState(null);
  const [selectedSignerIndex, setSelectedSignerIndex] = useState(0);
  const canvasRef = useRef(null);
  const containerRef = useRef(null);

  useEffect(() => {
    loadDocument();
  }, [documentId]);

  const loadDocument = async () => {
    try {
      const response = await getDocumentDownloadUrl(documentId);
      setPdfUrl(response.download_url);
      // In real implementation, use pdf.js to load and get page count
      setNumPages(3); // Placeholder
    } catch (error) {
      console.error('Failed to load document:', error);
    }
  };

  const handleDragStart = (fieldType) => {
    setDraggedField(fieldType);
  };

  const handleDrop = (e) => {
    e.preventDefault();
    if (!draggedField) return;

    const rect = e.currentTarget.getBoundingClientRect();
    const x = ((e.clientX - rect.left) / rect.width) * 100;
    const y = ((e.clientY - rect.top) / rect.height) * 100;

    const signer = signers[selectedSignerIndex];
    const newField = {
      id: `temp-${Date.now()}`,
      signer_id: signer.user_id,
      field_type: draggedField,
      page_number: currentPage,
      x: Math.max(0, Math.min(x, 90)),
      y: Math.max(0, Math.min(y, 90)),
      width: draggedField === 'initials' ? 15 : draggedField === 'date_signed' ? 20 : 30,
      height: 8,
      required: true
    };

    setFields([...fields, newField]);
    setDraggedField(null);
  };

  const handleFieldResize = (fieldId, newWidth, newHeight) => {
    setFields(fields.map(f => 
      f.id === fieldId ? { ...f, width: newWidth, height: newHeight } : f
    ));
  };

  const handleFieldMove = (fieldId, newX, newY) => {
    setFields(fields.map(f => 
      f.id === fieldId ? { ...f, x: newX, y: newY } : f
    ));
  };

  const handleDeleteField = (fieldId) => {
    setFields(fields.filter(f => f.id !== fieldId));
  };

  const handleSave = () => {
    if (fields.length === 0) {
      alert(t('esign.create.noFieldsPlaced'));
      return;
    }
    
    // Transform fields to API format
    const apiFields = fields.map(f => ({
      signer_id: f.signer_id,
      field_type: f.field_type,
      page_number: f.page_number,
      x: f.x,
      y: f.y,
      width: f.width,
      height: f.height,
      required: f.required
    }));
    
    onSave(apiFields);
  };

  const getUserName = (userId) => {
    const user = users?.find(u => u.id === userId);
    return user ? user.name : 'Unknown';
  };

  const pageFields = fields.filter(f => f.page_number === currentPage);

  return (
    <div className="flex flex-col h-full">
      {/* Toolbar */}
      <div className="border-b p-3 space-y-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <label className="text-sm font-medium">{t('esign.create.selectSigner')}:</label>
            <select
              value={selectedSignerIndex}
              onChange={(e) => setSelectedSignerIndex(parseInt(e.target.value))}
              className="border rounded px-2 py-1 text-sm"
            >
              {signers.map((signer, idx) => (
                <option key={idx} value={idx}>
                  {getUserName(signer.user_id)}
                </option>
              ))}
            </select>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-sm text-gray-600">
              {t('common.page')} {currentPage} / {numPages || 1}
            </span>
            <div className="flex gap-1">
              <Button
                size="sm"
                variant="outline"
                onClick={() => setCurrentPage(Math.max(1, currentPage - 1))}
                disabled={currentPage === 1}
              >
                ←
              </Button>
              <Button
                size="sm"
                variant="outline"
                onClick={() => setCurrentPage(Math.min(numPages || 1, currentPage + 1))}
                disabled={currentPage === (numPages || 1)}
              >
                →
              </Button>
            </div>
          </div>
        </div>

        {/* Field Palette */}
        <div className="flex gap-2 flex-wrap">
          {FIELD_TYPES.map(({ type, icon: Icon, label, color }) => (
            <div
              key={type}
              draggable
              onDragStart={() => handleDragStart(type)}
              className={`flex items-center gap-2 px-3 py-2 rounded border cursor-move ${color} hover:shadow-md transition-shadow`}
            >
              <Icon className="h-4 w-4" />
              <span className="text-sm font-medium">{label}</span>
            </div>
          ))}
        </div>
        <p className="text-xs text-gray-500">{t('esign.create.dragInstruction')}</p>
      </div>

      {/* PDF Canvas */}
      <div
        ref={containerRef}
        className="flex-1 overflow-auto bg-gray-100 p-4"
        onDrop={handleDrop}
        onDragOver={(e) => e.preventDefault()}
      >
        <div className="max-w-4xl mx-auto bg-white shadow-lg" style={{ aspectRatio: '8.5/11' }}>
          {/* PDF Page Preview */}
          <div className="relative w-full h-full border-2 border-gray-300">
            {!pdfUrl ? (
              <div className="absolute inset-0 flex items-center justify-center">
                <Loader2 className="h-8 w-8 animate-spin text-gray-400" />
              </div>
            ) : (
              <div className="absolute inset-0 bg-gray-50 flex items-center justify-center">
                <p className="text-gray-400">{t('esign.create.pdfPagePlaceholder', { page: currentPage })}</p>
              </div>
            )}

            {/* Placed Fields */}
            {pageFields.map((field) => {
              const fieldType = FIELD_TYPES.find(ft => ft.type === field.field_type);
              const Icon = fieldType?.icon;
              const isCurrentSigner = field.signer_id === signers[selectedSignerIndex]?.user_id;
              
              return (
                <div
                  key={field.id}
                  className={`absolute border-2 ${fieldType?.color} ${isCurrentSigner ? 'ring-2 ring-blue-500' : ''} cursor-move group`}
                  style={{
                    left: `${field.x}%`,
                    top: `${field.y}%`,
                    width: `${field.width}%`,
                    height: `${field.height}%`
                  }}
                  draggable
                  onDragEnd={(e) => {
                    const rect = containerRef.current?.getBoundingClientRect();
                    if (rect) {
                      const newX = ((e.clientX - rect.left) / rect.width) * 100;
                      const newY = ((e.clientY - rect.top) / rect.height) * 100;
                      handleFieldMove(field.id, Math.max(0, Math.min(newX, 90)), Math.max(0, Math.min(newY, 90)));
                    }
                  }}
                >
                  <div className="flex items-center justify-between h-full px-2 text-xs">
                    <div className="flex items-center gap-1">
                      {Icon && <Icon className="h-3 w-3" />}
                      <span className="font-medium truncate">{fieldType?.label}</span>
                    </div>
                    <button
                      onClick={() => handleDeleteField(field.id)}
                      className="opacity-0 group-hover:opacity-100 text-red-600 hover:text-red-800"
                    >
                      ×
                    </button>
                  </div>
                  {/* Resize handle */}
                  <div
                    className="absolute bottom-0 right-0 w-3 h-3 bg-blue-500 cursor-se-resize opacity-0 group-hover:opacity-100"
                    onMouseDown={(e) => {
                      e.stopPropagation();
                      // Implement resize logic
                    }}
                  />
                </div>
              );
            })}
          </div>
        </div>
      </div>

      {/* Summary */}
      <div className="border-t p-3 bg-gray-50">
        <div className="text-sm text-gray-600 mb-2">
          {t('esign.create.fieldsPlaced', { count: fields.length })}
        </div>
        {signers.map((signer, idx) => {
          const signerFields = fields.filter(f => f.signer_id === signer.user_id);
          return (
            <div key={idx} className="text-xs text-gray-500">
              {getUserName(signer.user_id)}: {signerFields.length} {t('esign.create.fields')}
            </div>
          );
        })}
      </div>

      {/* Actions */}
      <div className="border-t p-3 flex justify-end gap-2">
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
