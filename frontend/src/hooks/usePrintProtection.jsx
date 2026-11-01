import { useEffect } from 'react';

const STYLE_ID = 'share-link-print-protection-styles';

const PRINT_PROTECTION_CSS = `
@media print {
  body * {
    visibility: hidden !important;
  }
  .share-link-print-disabled-notice,
  .share-link-print-disabled-notice * {
    visibility: visible !important;
  }
  .share-link-print-disabled-notice {
    position: fixed;
    inset: 0;
    display: flex !important;
    align-items: center;
    justify-content: center;
    font-size: 1.25rem;
    font-family: system-ui, sans-serif;
  }
}
`;

function isPrintShortcut(event) {
  if (!(event.ctrlKey || event.metaKey)) {
    return false;
  }
  const key = event.key?.toLowerCase();
  return key === 'p';
}

/**
 * When enabled, blocks browser print shortcuts and injects print-hiding CSS.
 */
export function usePrintProtection(enabled) {
  useEffect(() => {
    if (!enabled) {
      return undefined;
    }

    let styleEl = document.getElementById(STYLE_ID);
    if (!styleEl) {
      styleEl = document.createElement('style');
      styleEl.id = STYLE_ID;
      styleEl.textContent = PRINT_PROTECTION_CSS;
      document.head.appendChild(styleEl);
    }

    const onKeyDown = (event) => {
      if (isPrintShortcut(event)) {
        event.preventDefault();
        event.stopPropagation();
      }
    };

    const onContextMenu = (event) => {
      if (event.target.closest('[data-viewer-content]')) {
        event.preventDefault();
      }
    };

    const onDragStart = (event) => {
      if (event.target.closest('[data-viewer-content]')) {
        event.preventDefault();
      }
    };

    window.addEventListener('keydown', onKeyDown, true);
    document.addEventListener('contextmenu', onContextMenu, true);
    document.addEventListener('dragstart', onDragStart, true);

    return () => {
      window.removeEventListener('keydown', onKeyDown, true);
      document.removeEventListener('contextmenu', onContextMenu, true);
      document.removeEventListener('dragstart', onDragStart, true);
      styleEl?.remove();
    };
  }, [enabled]);
}

export function PrintDisabledNotice({ message }) {
  if (!message) {
    return null;
  }
  return (
    <div
      className="share-link-print-disabled-notice pointer-events-none fixed -left-[9999px] h-0 w-0 overflow-hidden"
      aria-hidden="true"
    >
      {message}
    </div>
  );
}
