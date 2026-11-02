/**
 * Convert a pointer position within a page element to percentage coordinates
 * (top-left origin), matching backend SignatureField x/y storage.
 */
export function clientPointToFieldPercent(rect, clientX, clientY) {
  if (!rect || rect.width <= 0 || rect.height <= 0) {
    return { x: 0, y: 0 };
  }
  const x = ((clientX - rect.left) / rect.width) * 100;
  const y = ((clientY - rect.top) / rect.height) * 100;
  return {
    x: clampPercent(x),
    y: clampPercent(y),
  };
}

export function clampPercent(value, max = 95) {
  return Math.max(0, Math.min(value, max));
}

export function defaultFieldSize(fieldType) {
  if (fieldType === 'initials') {
    return { width: 15, height: 8 };
  }
  if (fieldType === 'date_signed') {
    return { width: 20, height: 8 };
  }
  return { width: 30, height: 8 };
}

/** Stable color classes per signer id (e-sign integer). */
export const SIGNER_OVERLAY_COLORS = [
  'bg-blue-100/90 border-blue-500',
  'bg-green-100/90 border-green-500',
  'bg-purple-100/90 border-purple-500',
  'bg-orange-100/90 border-orange-500',
  'bg-pink-100/90 border-pink-500',
  'bg-teal-100/90 border-teal-500',
];

export function signerOverlayColor(signerId, signerIdsInOrder = []) {
  const index = signerIdsInOrder.indexOf(signerId);
  const idx = index >= 0 ? index : Math.abs(Number(signerId) || 0) % SIGNER_OVERLAY_COLORS.length;
  return SIGNER_OVERLAY_COLORS[idx % SIGNER_OVERLAY_COLORS.length];
}
