import { render } from '@testing-library/react';
import { describe, expect, it, afterEach } from 'vitest';
import { usePrintProtection } from '../../hooks/usePrintProtection';

function ProtectionHarness({ enabled }) {
  usePrintProtection(enabled);
  return <div data-viewer-content>Viewer</div>;
}

describe('usePrintProtection', () => {
  afterEach(() => {
    document.getElementById('share-link-print-protection-styles')?.remove();
  });

  it('blocks Ctrl+P when enabled', () => {
    render(<ProtectionHarness enabled />);
    expect(document.getElementById('share-link-print-protection-styles')).toBeTruthy();

    let defaultPrevented = false;
    const event = new KeyboardEvent('keydown', {
      key: 'p',
      ctrlKey: true,
      bubbles: true,
      cancelable: true,
    });
    event.preventDefault = () => {
      defaultPrevented = true;
    };
    window.dispatchEvent(event);

    expect(defaultPrevented).toBe(true);
  });

  it('does not block Ctrl+P when disabled', () => {
    render(<ProtectionHarness enabled={false} />);

    const event = new KeyboardEvent('keydown', { key: 'p', ctrlKey: true, bubbles: true, cancelable: true });
    let defaultPrevented = false;
    window.addEventListener(
      'keydown',
      (e) => {
        if (e.defaultPrevented) {
          defaultPrevented = true;
        }
      },
      { once: true, capture: true },
    );
    window.dispatchEvent(event);

    expect(defaultPrevented).toBe(false);
  });
});
