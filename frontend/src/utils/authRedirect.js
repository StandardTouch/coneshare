/**
 * Builds a same-origin relative path safe for post-login navigation.
 * Rejects protocol-relative paths (//...) and non-path values.
 */
export function getSafeRedirectTarget(fromLocation) {
  if (!fromLocation || typeof fromLocation.pathname !== 'string') {
    return '/';
  }

  const { pathname, search = '', hash = '' } = fromLocation;

  if (!pathname.startsWith('/') || pathname.startsWith('//')) {
    return '/';
  }

  return `${pathname}${search}${hash}`;
}
