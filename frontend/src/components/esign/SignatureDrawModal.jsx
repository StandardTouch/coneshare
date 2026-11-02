import { useRef, useEffect, useState, useCallback } from 'react';
import { useTranslation } from 'react-i18next';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from '../ui/Dialog';
import { Button } from '../ui/Button';

const CANVAS_HEIGHT_PX = 200;

export function SignatureDrawModal({ isOpen, onOpenChange, onSave, fieldType = 'signature' }) {
  const { t } = useTranslation();
  const canvasRef = useRef(null);
  const ctxRef = useRef(null);
  const isDrawingRef = useRef(false);
  const [hasDrawn, setHasDrawn] = useState(false);

  const syncCanvasSize = useCallback(() => {
    const canvas = canvasRef.current;
    if (!canvas) return false;

    const dpr = window.devicePixelRatio || 1;
    const rect = canvas.getBoundingClientRect();
    const displayWidth = Math.max(1, Math.floor(rect.width));
    const displayHeight = Math.max(1, Math.floor(rect.height));

    canvas.width = Math.round(displayWidth * dpr);
    canvas.height = Math.round(displayHeight * dpr);

    const ctx = canvas.getContext('2d');
    if (!ctx) return false;

    ctx.setTransform(1, 0, 0, 1, 0, 0);
    ctx.scale(dpr, dpr);
    ctx.strokeStyle = '#000000';
    ctx.lineWidth = 2;
    ctx.lineCap = 'round';
    ctx.lineJoin = 'round';
    ctxRef.current = ctx;
    return true;
  }, []);

  useEffect(() => {
    if (!isOpen) {
      ctxRef.current = null;
      isDrawingRef.current = false;
      setHasDrawn(false);
      return undefined;
    }

    let cancelled = false;
    const ensureReady = () => {
      if (cancelled) return;
      const ok = syncCanvasSize();
      if (!ok) {
        requestAnimationFrame(ensureReady);
      }
    };
    requestAnimationFrame(ensureReady);

    const canvas = canvasRef.current;
    const ro =
      canvas && typeof ResizeObserver !== 'undefined'
        ? new ResizeObserver(() => {
            if (isOpen && !isDrawingRef.current) {
              syncCanvasSize();
            }
          })
        : null;
    if (canvas && ro) ro.observe(canvas);

    return () => {
      cancelled = true;
      ro?.disconnect();
    };
  }, [isOpen, syncCanvasSize]);

  const getCanvasPoint = (event) => {
    const canvas = canvasRef.current;
    const rect = canvas.getBoundingClientRect();
    return {
      x: event.clientX - rect.left,
      y: event.clientY - rect.top,
    };
  };

  const handlePointerDown = (event) => {
    if (event.pointerType === 'mouse' && event.button !== 0) return;
    event.preventDefault();

    if (!ctxRef.current) {
      syncCanvasSize();
    }
    const ctx = ctxRef.current;
    if (!ctx) return;

    try {
      event.currentTarget.setPointerCapture(event.pointerId);
    } catch {
      // jsdom and some browsers may not support pointer capture
    }
    const { x, y } = getCanvasPoint(event);
    isDrawingRef.current = true;
    setHasDrawn(true);
    ctx.beginPath();
    ctx.moveTo(x, y);
  };

  const handlePointerMove = (event) => {
    if (!isDrawingRef.current || !ctxRef.current) return;
    event.preventDefault();
    const { x, y } = getCanvasPoint(event);
    const ctx = ctxRef.current;
    ctx.lineTo(x, y);
    ctx.stroke();
  };

  const endStroke = (event) => {
    if (!isDrawingRef.current) return;
    isDrawingRef.current = false;
    if (event?.currentTarget?.hasPointerCapture?.(event.pointerId)) {
      event.currentTarget.releasePointerCapture(event.pointerId);
    }
  };

  const handleClear = () => {
    const canvas = canvasRef.current;
    const ctx = ctxRef.current;
    if (canvas && ctx) {
      const dpr = window.devicePixelRatio || 1;
      ctx.clearRect(0, 0, canvas.width / dpr, canvas.height / dpr);
      setHasDrawn(false);
    }
  };

  const handleSave = () => {
    if (!canvasRef.current || !hasDrawn) return;
    const dataUrl = canvasRef.current.toDataURL('image/png');
    onSave(dataUrl);
    onOpenChange(false);
  };

  const handleClose = () => {
    handleClear();
    onOpenChange(false);
  };

  return (
    <Dialog open={isOpen} onOpenChange={handleClose}>
      <DialogContent className="sm:max-w-2xl">
        <DialogHeader>
          <DialogTitle>
            {fieldType === 'signature' ? t('esign.signature.drawSignature') : t('esign.signature.drawInitials')}
          </DialogTitle>
          <DialogDescription>{t('esign.signature.drawInstruction')}</DialogDescription>
        </DialogHeader>

        <div className="py-4">
          <div className="border-2 border-gray-300 rounded-lg bg-white mb-4">
            <canvas
              ref={canvasRef}
              className="block w-full cursor-crosshair touch-none"
              style={{ height: CANVAS_HEIGHT_PX, touchAction: 'none' }}
              onPointerDown={handlePointerDown}
              onPointerMove={handlePointerMove}
              onPointerUp={endStroke}
              onPointerCancel={endStroke}
              onPointerLeave={endStroke}
            />
          </div>
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={handleClear}>
            {t('esign.signature.clear')}
          </Button>
          <Button variant="outline" onClick={handleClose}>
            {t('common.cancel')}
          </Button>
          <Button onClick={handleSave} disabled={!hasDrawn}>
            {t('common.save')}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
