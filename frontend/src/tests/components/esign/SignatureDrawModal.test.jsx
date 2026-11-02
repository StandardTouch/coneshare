import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';

import '../../../i18n';
import { SignatureDrawModal } from '../../../components/esign/SignatureDrawModal';

function createMockContext() {
  return {
    setTransform: vi.fn(),
    scale: vi.fn(),
    strokeStyle: '',
    lineWidth: 0,
    lineCap: '',
    lineJoin: '',
    beginPath: vi.fn(),
    moveTo: vi.fn(),
    lineTo: vi.fn(),
    stroke: vi.fn(),
    clearRect: vi.fn(),
  };
}

describe('SignatureDrawModal', () => {
  beforeEach(() => {
    vi.spyOn(HTMLCanvasElement.prototype, 'getContext').mockImplementation(function mockGetContext(type) {
      if (type === '2d') {
        return createMockContext();
      }
      return null;
    });
    vi.spyOn(HTMLCanvasElement.prototype, 'getBoundingClientRect').mockReturnValue({
      width: 400,
      height: 200,
      top: 0,
      left: 0,
      right: 400,
      bottom: 200,
      x: 0,
      y: 0,
      toJSON: () => ({}),
    });
  });

  it('enables save after pointer drawing on the canvas', async () => {
    const onSave = vi.fn();
    render(
      <SignatureDrawModal isOpen onOpenChange={vi.fn()} onSave={onSave} fieldType="signature" />
    );

    const saveButton = screen.getByRole('button', { name: /save changes/i });
    expect(saveButton).toBeDisabled();

    const canvas = document.querySelector('canvas');
    expect(canvas).toBeTruthy();

    await waitFor(() => {
      expect(canvas.width).toBeGreaterThan(0);
    });

    fireEvent.pointerDown(canvas, {
      clientX: 50,
      clientY: 50,
      pointerId: 1,
      buttons: 1,
      button: 0,
      pointerType: 'mouse',
    });
    fireEvent.pointerMove(canvas, {
      clientX: 120,
      clientY: 80,
      pointerId: 1,
      buttons: 1,
      button: 0,
      pointerType: 'mouse',
    });
    fireEvent.pointerUp(canvas, {
      clientX: 120,
      clientY: 80,
      pointerId: 1,
      button: 0,
      pointerType: 'mouse',
    });

    await waitFor(() => {
      expect(saveButton).not.toBeDisabled();
    });
  });

  it('exposes an accessible dialog description', () => {
    render(
      <SignatureDrawModal isOpen onOpenChange={vi.fn()} onSave={vi.fn()} fieldType="initials" />
    );

    expect(
      screen.getByText(/use your mouse or touch screen to draw/i)
    ).toBeInTheDocument();
  });
});
