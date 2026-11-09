import {
  forwardRef,
  useCallback,
  useEffect,
  useImperativeHandle,
  useRef,
  useState,
} from 'react';
import { useTranslation } from 'react-i18next';
import { Loader2 } from 'lucide-react';
import { useEsignPdfDocument } from '../../hooks/useEsignPdfDocument';
import { PdfPage } from '../documents/PdfPage';
import { Button } from '../ui/Button';
import { Input } from '../ui/Input';
import { fieldOriginFromClient, fieldSizeFromCorner, signerOverlayColor } from './fieldPlacementUtils';
import { EsignPdfThumbnailSidebar } from './EsignPdfThumbnailSidebar';

const MIN_PAGE_SCALE = 0.6;
const MAX_PAGE_SCALE = 1.35;

/**
 * Shared pdf.js viewer for e-sign placement and signing flows.
 * Virtualized page list with optional thumbnails and field overlays.
 */
export const EsignPdfViewer = forwardRef(function EsignPdfViewer(
  {
    pdfUrl,
    mode = 'view',
    fields = [],
    activeSignerId = null,
    currentUserSignerId = null,
    filledFieldIds = new Set(),
    onFieldClick,
    onPageDrop,
    onFieldMove,
    onFieldDelete,
    scrollToFieldId = null,
    showThumbnails = false,
    showPageControls = true,
    className = '',
  },
  ref
) {
  const { t } = useTranslation();
  const { pdfDoc, numPages, loading, error } = useEsignPdfDocument(pdfUrl);
  const [scrollContainer, setScrollContainer] = useState(null);
  const [currentPage, setCurrentPage] = useState(1);
  const [pageInput, setPageInput] = useState('1');
  const [pageScale, setPageScale] = useState(1);
  const pageRefs = useRef(new Map());
  const interactionRef = useRef(null);

  const scrollContainerRef = useCallback((node) => {
    if (node) {
      setScrollContainer(node);
    }
  }, []);

  const signerIdsInOrder = [...new Set(fields.map((f) => f.signer_id))];

  useImperativeHandle(ref, () => ({
    goToPage: (pageNumber) => {
      const el = pageRefs.current.get(pageNumber);
      if (el) {
        el.scrollIntoView({ behavior: 'smooth', block: 'start' });
      }
    },
    goToField: (field) => {
      if (!field) return;
      const el = pageRefs.current.get(field.page_number);
      if (el) {
        el.scrollIntoView({ behavior: 'smooth', block: 'center' });
      }
    },
  }));

  useEffect(() => {
    if (!scrollContainer || !pdfDoc) return;
    scrollContainer.scrollTop = 0;
    setCurrentPage(1);
    setPageInput('1');
  }, [pdfDoc, scrollContainer]);

  useEffect(() => {
    if (!scrollContainer || !pdfDoc) return undefined;
    let cancelled = false;
    pdfDoc.getPage(1).then((page) => {
      if (cancelled) return;
      const viewport = page.getViewport({ scale: 1 });
      if (!viewport.width) return;
      const available = Math.max(280, scrollContainer.clientWidth - 48);
      const fitted = available / viewport.width;
      setPageScale(Math.min(MAX_PAGE_SCALE, Math.max(MIN_PAGE_SCALE, fitted)));
    }).catch(() => {});
    return () => {
      cancelled = true;
    };
  }, [pdfDoc, scrollContainer]);

  useEffect(() => {
    if (!scrollContainer || !numPages) return undefined;

    const observer = new IntersectionObserver(
      (entries) => {
        const visible = entries
          .filter((e) => e.isIntersecting)
          .sort((a, b) => b.intersectionRatio - a.intersectionRatio);
        if (visible.length > 0) {
          const page = parseInt(visible[0].target.dataset.pageNumber, 10);
          if (!Number.isNaN(page)) {
            setCurrentPage(page);
            setPageInput(String(page));
          }
        }
      },
      { root: scrollContainer, threshold: [0.35, 0.5, 0.75] }
    );

    pageRefs.current.forEach((el) => {
      if (el) observer.observe(el);
    });

    return () => observer.disconnect();
  }, [numPages, scrollContainer]);

  useEffect(() => {
    if (!scrollToFieldId || !fields.length) return;
    const target = fields.find((f) => f.id === scrollToFieldId);
    if (target) {
      const el = pageRefs.current.get(target.page_number);
      if (el) {
        el.scrollIntoView({ behavior: 'smooth', block: 'center' });
      }
    }
  }, [scrollToFieldId, fields, pdfDoc]);

  const handleJumpToPage = () => {
    const parsed = parseInt(pageInput, 10);
    if (Number.isNaN(parsed)) return;
    const page = Math.max(1, Math.min(numPages || 1, parsed));
    const el = pageRefs.current.get(page);
    if (el) {
      el.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
  };

  const handleJumpToLast = () => {
    if (!numPages) return;
    const el = pageRefs.current.get(numPages);
    if (el) {
      el.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
  };

  const handleSelectPage = (pageNumber) => {
    const el = pageRefs.current.get(pageNumber);
    if (el) {
      el.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
  };

  if (!pdfUrl) {
    return null;
  }

  if (loading) {
    return (
      <div className="flex flex-1 items-center justify-center bg-gray-100 p-8">
        <Loader2 className="h-8 w-8 animate-spin text-gray-400" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex flex-1 items-center justify-center bg-gray-100 p-8 text-center text-red-600">
        <p>{t('esign.viewer.loadFailed')}</p>
      </div>
    );
  }

  const applyInteraction = (clientX, clientY) => {
    const interaction = interactionRef.current;
    if (!interaction || !onFieldMove) return;
    const rect = interaction.pageEl.getBoundingClientRect();
    if (interaction.kind === 'resize') {
      onFieldMove(interaction.id, fieldSizeFromCorner(interaction.origin, rect, clientX, clientY));
      return;
    }
    onFieldMove(
      interaction.id,
      fieldOriginFromClient(
        rect,
        clientX - interaction.dx,
        clientY - interaction.dy,
        interaction.width,
        interaction.height,
      ),
    );
  };

  const renderFieldOverlay = (field) => {
    const isOwnField = currentUserSignerId != null && field.signer_id === currentUserSignerId;
    const isActiveSigner = activeSignerId != null && field.signer_id === activeSignerId;
    const isFilled = filledFieldIds.has(field.id);
    const readOnly = mode === 'signing' && !isOwnField;
    const colorClass = signerOverlayColor(field.signer_id, signerIdsInOrder);

    let ringClass = '';
    if (mode === 'placement' && isActiveSigner) {
      ringClass = 'ring-2 ring-blue-600';
    } else if (mode === 'signing' && isOwnField) {
      ringClass = isFilled ? 'ring-2 ring-green-500' : 'ring-2 ring-yellow-400 animate-pulse';
    }

    const Wrapper = mode === 'signing' && !readOnly ? 'button' : 'div';

    return (
      <Wrapper
        key={field.id}
        type={Wrapper === 'button' ? 'button' : undefined}
        disabled={readOnly}
        onClick={() => {
          if (mode === 'signing' && !readOnly && onFieldClick) {
            onFieldClick(field);
          }
        }}
        onPointerDown={(e) => {
          if (mode !== 'placement' || !onFieldMove) return;
          if (e.target.closest('[data-esign-resize], [data-esign-delete]')) return;
          const pageEl = e.currentTarget.closest('[data-page-number]');
          if (!pageEl) return;
          const fieldRect = e.currentTarget.getBoundingClientRect();
          interactionRef.current = {
            kind: 'move',
            id: field.id,
            pageEl,
            dx: e.clientX - fieldRect.left,
            dy: e.clientY - fieldRect.top,
            width: field.width,
            height: field.height,
          };
          e.currentTarget.setPointerCapture(e.pointerId);
        }}
        onPointerMove={(e) => {
          if (interactionRef.current?.kind !== 'move' || interactionRef.current.id !== field.id) return;
          applyInteraction(e.clientX, e.clientY);
        }}
        onPointerUp={() => {
          if (interactionRef.current?.id === field.id) {
            interactionRef.current = null;
          }
        }}
        className={`absolute border-2 text-left text-xs px-1 py-0.5 overflow-hidden group touch-none ${colorClass} ${ringClass} ${
          readOnly ? 'cursor-default opacity-70' : mode === 'signing' ? 'cursor-pointer hover:brightness-95' : 'cursor-move'
        }`}
        style={{
          left: `${field.x}%`,
          top: `${field.y}%`,
          width: `${field.width}%`,
          height: `${field.height}%`,
        }}
        data-testid={`esign-field-${field.id}`}
      >
        <span className="font-medium truncate block">{field.field_type}</span>
        {mode === 'placement' && onFieldDelete && (
          <button
            type="button"
            data-esign-delete
            className="absolute top-0 right-0 hidden group-hover:block bg-red-600 text-white text-[10px] leading-none px-1 rounded-bl"
            onPointerDown={(e) => e.stopPropagation()}
            onClick={(e) => {
              e.stopPropagation();
              onFieldDelete(field.id);
            }}
          >
            ×
          </button>
        )}
        {mode === 'placement' && onFieldMove && (
          <button
            type="button"
            data-esign-resize
            aria-label={t('esign.viewer.resizeField')}
            className="absolute bottom-0 right-0 h-3 w-3 cursor-se-resize bg-blue-600"
            onPointerDown={(e) => {
              e.stopPropagation();
              e.preventDefault();
              const pageEl = e.currentTarget.closest('[data-page-number]');
              if (!pageEl) return;
              interactionRef.current = {
                kind: 'resize',
                id: field.id,
                pageEl,
                origin: { x: field.x, y: field.y },
              };
              e.currentTarget.setPointerCapture(e.pointerId);
            }}
            onPointerMove={(e) => {
              if (interactionRef.current?.kind !== 'resize' || interactionRef.current.id !== field.id) return;
              applyInteraction(e.clientX, e.clientY);
            }}
            onPointerUp={() => {
              if (interactionRef.current?.id === field.id) {
                interactionRef.current = null;
              }
            }}
          />
        )}
      </Wrapper>
    );
  };

  const pageList = (
    <div className="mx-auto flex w-fit flex-col items-center gap-4 p-4">
      {Array.from({ length: numPages }, (_, i) => {
        const pageNumber = i + 1;
        const pageFields = fields.filter((f) => f.page_number === pageNumber);

        return (
          <div
            key={pageNumber}
            ref={(node) => {
              if (node) {
                pageRefs.current.set(pageNumber, node);
              } else {
                pageRefs.current.delete(pageNumber);
              }
            }}
            data-page-number={pageNumber}
            className="relative"
            onDragOver={(e) => {
              if (mode === 'placement' && onPageDrop) {
                e.preventDefault();
              }
            }}
            onDrop={(e) => {
              if (mode === 'placement' && onPageDrop) {
                e.preventDefault();
                onPageDrop(e, pageNumber);
              }
            }}
          >
            <PdfPage
              pdfDoc={pdfDoc}
              pageNumber={pageNumber}
              scale={pageScale}
              scrollContainer={scrollContainer}
              dimensions={null}
              lockToCanvas
            />
            {pageFields.map(renderFieldOverlay)}
          </div>
        );
      })}
    </div>
  );

  return (
    <div className={`flex flex-col h-full min-h-0 ${className}`}>
      {showPageControls && numPages > 0 && (
        <div className="flex flex-wrap items-center gap-2 border-b bg-white px-3 py-2 text-sm">
          <span>
            {t('common.page')} {currentPage} / {numPages}
          </span>
          <div className="flex items-center gap-1">
            <Input
              className="h-8 w-16 px-2"
              value={pageInput}
              onChange={(e) => setPageInput(e.target.value.replace(/\D/g, ''))}
              onKeyDown={(e) => {
                if (e.key === 'Enter') handleJumpToPage();
              }}
              aria-label={t('esign.viewer.pageJump')}
            />
            <Button size="sm" variant="outline" type="button" onClick={handleJumpToPage}>
              {t('esign.viewer.go')}
            </Button>
          </div>
          <Button size="sm" variant="outline" type="button" onClick={handleJumpToLast}>
            {t('esign.viewer.jumpToLastPage')}
          </Button>
        </div>
      )}

      <div className="flex flex-1 min-h-0">
        {showThumbnails && (
          <EsignPdfThumbnailSidebar
            pdfDoc={pdfDoc}
            numPages={numPages}
            currentPage={currentPage}
            fields={fields}
            onPageSelect={handleSelectPage}
          />
        )}

        <div ref={scrollContainerRef} className="flex-1 overflow-y-auto bg-gray-100 min-h-0">
          {pageList}
        </div>
      </div>
    </div>
  );
});
