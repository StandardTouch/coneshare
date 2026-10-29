import api from './api';

/**
 * E-Signature API Service
 * 
 * Handles all API calls related to electronic signature requests.
 * Phase 1: Internal users only, authentication required.
 */

// ==================== Signature Requests (Authenticated) ====================

/**
 * List signature requests
 * @param {string} view - 'created' (default) or 'awaiting' (requests where user is a signer)
 */
export const listSignatureRequests = async (view = 'created') => {
  const response = await api.get('/esign/requests/', {
    params: { view }
  });
  return response.data;
};

/**
 * Get signature request details
 */
export const getSignatureRequest = async (requestId) => {
  const response = await api.get(`/esign/requests/${requestId}/`);
  return response.data;
};

/**
 * Create a new signature request (draft status)
 */
export const createSignatureRequest = async (data) => {
  // data: { document_id, title, message, signers: [{user_id, signing_order}], signing_order: bool, expires_at }
  const response = await api.post('/esign/requests/', data);
  return response.data;
};

/**
 * Update signature fields for a draft request
 */
export const updateSignatureFields = async (requestId, fields) => {
  // fields: [{ signer_id, field_type, page_number, x, y, width, height, label?, required? }]
  const response = await api.patch(`/esign/requests/${requestId}/update_fields/`, {
    fields
  });
  return response.data;
};

/**
 * Send signature request to signers
 */
export const sendSignatureRequest = async (requestId) => {
  const response = await api.post(`/esign/requests/${requestId}/send/`);
  return response.data;
};

/**
 * Cancel signature request
 */
export const cancelSignatureRequest = async (requestId) => {
  const response = await api.post(`/esign/requests/${requestId}/cancel/`);
  return response.data;
};

/**
 * Send reminder to pending signers
 */
export const sendReminder = async (requestId) => {
  const response = await api.post(`/esign/requests/${requestId}/remind/`);
  return response.data;
};

/**
 * Get download URL for signed document
 */
export const downloadSignedDocument = async (requestId) => {
  const response = await api.get(`/esign/requests/${requestId}/download_signed/`);
  return response.data;
};

/**
 * Get download URL for certificate of completion
 */
export const downloadCertificate = async (requestId) => {
  const response = await api.get(`/esign/requests/${requestId}/download_certificate/`);
  return response.data;
};

// ==================== Signing Workflow (Authenticated) ====================

/**
 * Get signing page data by token (user must be authenticated and be the assigned signer)
 */
export const getSigningData = async (token) => {
  const response = await api.get(`/esign/sign/${token}/`);
  return response.data;
};

/**
 * Request OTP for signing
 */
export const requestOTP = async (token) => {
  const response = await api.post(`/esign/sign/${token}/request_otp/`);
  return response.data;
};

/**
 * Verify OTP code
 */
export const verifyOTP = async (token, code) => {
  const response = await api.post(`/esign/sign/${token}/verify_otp/`, { code });
  return response.data;
};

/**
 * Submit signature
 * @param {string} token - Signer token
 * @param {Array} fields - Array of { field_id, value } where value is signature data or text
 */
export const submitSignature = async (token, fields) => {
  const response = await api.post(`/esign/sign/${token}/submit/`, { fields });
  return response.data;
};

/**
 * Decline to sign
 */
export const declineToSign = async (token, reason = '') => {
  const response = await api.post(`/esign/sign/${token}/decline/`, { reason });
  return response.data;
};

// ==================== Field Templates (Optional) ====================

/**
 * List field templates
 */
export const listFieldTemplates = async () => {
  const response = await api.get('/esign/templates/');
  return response.data;
};

/**
 * Get field template
 */
export const getFieldTemplate = async (templateId) => {
  const response = await api.get(`/esign/templates/${templateId}/`);
  return response.data;
};

/**
 * Create field template
 */
export const createFieldTemplate = async (data) => {
  // data: { name, description, config }
  const response = await api.post('/esign/templates/', data);
  return response.data;
};

/**
 * Delete field template
 */
export const deleteFieldTemplate = async (templateId) => {
  await api.delete(`/esign/templates/${templateId}/`);
};

// ==================== Helper Functions ====================

/**
 * Convert canvas signature to data URL
 */
export const canvasToDataURL = (canvas) => {
  return canvas.toDataURL('image/png');
};

/**
 * Field type display names
 */
export const FIELD_TYPE_LABELS = {
  signature: 'Signature',
  initials: 'Initials',
  date_signed: 'Date Signed',
  full_name: 'Full Name',
  text: 'Text'
};

/**
 * Status badge colors
 */
export const STATUS_COLORS = {
  draft: 'bg-gray-100 text-gray-800',
  sent: 'bg-blue-100 text-blue-800',
  in_progress: 'bg-yellow-100 text-yellow-800',
  completed: 'bg-green-100 text-green-800',
  declined: 'bg-red-100 text-red-800',
  cancelled: 'bg-gray-100 text-gray-600',
  expired: 'bg-orange-100 text-orange-800'
};

/**
 * Signer status colors
 */
export const SIGNER_STATUS_COLORS = {
  pending: 'bg-gray-100 text-gray-600',
  sent: 'bg-blue-100 text-blue-800',
  viewed: 'bg-purple-100 text-purple-800',
  otp_verified: 'bg-indigo-100 text-indigo-800',
  signed: 'bg-green-100 text-green-800',
  declined: 'bg-red-100 text-red-800'
};

export default {
  listSignatureRequests,
  getSignatureRequest,
  createSignatureRequest,
  updateSignatureFields,
  sendSignatureRequest,
  cancelSignatureRequest,
  sendReminder,
  downloadSignedDocument,
  downloadCertificate,
  getSigningData,
  requestOTP,
  verifyOTP,
  submitSignature,
  declineToSign,
  listFieldTemplates,
  getFieldTemplate,
  createFieldTemplate,
  deleteFieldTemplate,
  canvasToDataURL,
  FIELD_TYPE_LABELS,
  STATUS_COLORS,
  SIGNER_STATUS_COLORS
};
