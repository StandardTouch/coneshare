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
  return { x, y };
}

export function clampPercent(value, max = 95) {
  return Math.max(0, Math.min(value, max));
}

/**
 * Keep a field box fully on the page. x/y are the top-left, in percent.
 */
export function clampFieldBox({ x, y, width, height }) {
  const safeWidth = Math.min(100, Math.max(4, width));
  const safeHeight = Math.min(100, Math.max(2, height));
  return {
    x: clampPercent(x, Math.max(0, 100 - safeWidth)),
    y: clampPercent(y, Math.max(0, 100 - safeHeight)),
    width: safeWidth,
    height: safeHeight,
  };
}

/** Place a new field so its center sits on the pointer, then keep it on the page. */
export function placeFieldAtClient(rect, clientX, clientY, size) {
  const point = clientPointToFieldPercent(rect, clientX, clientY);
  return clampFieldBox({
    x: point.x - size.width / 2,
    y: point.y - size.height / 2,
    width: size.width,
    height: size.height,
  });
}

/**
 * Move a field so its top-left follows a screen point.
 * Pass the pointer minus the grab offset so the box does not jump.
 */
export function fieldOriginFromClient(rect, clientX, clientY, width, height) {
  const point = clientPointToFieldPercent(rect, clientX, clientY);
  return clampFieldBox({ x: point.x, y: point.y, width, height });
}

/** Resize from a fixed top-left so the bottom-right corner follows the pointer. */
export function fieldSizeFromCorner(origin, rect, clientX, clientY) {
  const point = clientPointToFieldPercent(rect, clientX, clientY);
  return clampFieldBox({
    x: origin.x,
    y: origin.y,
    width: point.x - origin.x,
    height: point.y - origin.y,
  });
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

function stableSignerColorIndex(signerId) {
  const id = String(signerId ?? '');
  let hash = 0;
  for (let i = 0; i < id.length; i += 1) {
    hash = (hash * 31 + id.charCodeAt(i)) >>> 0;
  }
  return hash % SIGNER_OVERLAY_COLORS.length;
}

export function signerOverlayColor(signerId, signerIdsInOrder = []) {
  const index = signerIdsInOrder.indexOf(signerId);
  const idx = index >= 0 ? index : stableSignerColorIndex(signerId);
  return SIGNER_OVERLAY_COLORS[idx % SIGNER_OVERLAY_COLORS.length];
}
