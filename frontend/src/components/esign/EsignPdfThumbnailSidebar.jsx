import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { Skeleton } from '../ui/Skeleton';

const THUMB_MAX_WIDTH = 96;
const THUMB_SCALE = 0.12;
const THUMB_ROOT_MARGIN = '600px 0px';
const THUMB_CACHE_MAX = 40;

/**
 * LRU cache of rendered thumbnail data URLs keyed by page number.
 */
function createThumbnailCache(maxEntries) {
  const map = new Map();
  return {
    get(page) {
      if (!map.has(page)) return null;
      const value = map.get(page);
      map.delete(page);
      map.set(page, value);
      return value;
    },
    set(page, dataUrl) {
      if (map.has(page)) map.delete(page);
      map.set(page, dataUrl);
      while (map.size > maxEntries) {
        const oldest = map.keys().next().value;
        map.delete(oldest);
      }
    },
    has(page) {
      return map.has(page);
    },
  };
}

function EsignPdfThumbnailItem({
  pageNumber,
  pdfDoc,
  scrollRoot,
  isActive,
  hasFields,
  onSelect,
  cache,
}) {
  const containerRef = useRef(null);
  const canvasRef = useRef(null);
  const renderTaskRef = useRef(null);
  const [isVisible, setIsVisible] = useState(false);
  const [rendered, setRendered] = useState(false);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!scrollRoot) return undefined;
    const el = containerRef.current;
    if (!el) return undefined;

    const observer = new IntersectionObserver(
      (entries) => setIsVisible(entries[0]?.isIntersecting ?? false),
      { root: scrollRoot, rootMargin: THUMB_ROOT_MARGIN, threshold: 0.01 }
    );
    observer.observe(el);
    return () => observer.disconnect();
  }, [scrollRoot]);

  useEffect(() => {
    if (!isVisible || !pdfDoc) {
      if (renderTaskRef.current) {
        renderTaskRef.current.cancel();
        renderTaskRef.current = null;
      }
      setRendered(false);
      setLoading(false);
      return undefined;
    }

    const cached = cache.get(pageNumber);
    if (cached && canvasRef.current) {
      const img = new Image();
      img.onload = () => {
        const canvas = canvasRef.current;
        if (!canvas) return;
        canvas.width = img.width;
        canvas.height = img.height;
        const ctx = canvas.getContext('2d');
        ctx?.drawImage(img, 0, 0);
        setRendered(true);
      };
      img.src = cached;
      return undefined;
    }

    let cancelled = false;
    setLoading(true);

    pdfDoc.getPage(pageNumber).then((page) => {
      if (cancelled) return;
      const viewport = page.getViewport({ scale: THUMB_SCALE });
      const canvas = canvasRef.current;
      if (!canvas) return;

      const context = canvas.getContext('2d');
      if (!context) return;

      canvas.width = Math.floor(viewport.width);
      canvas.height = Math.floor(viewport.height);

      if (renderTaskRef.current) {
        renderTaskRef.current.cancel();
      }

      const task = page.render({ canvasContext: context, viewport });
      renderTaskRef.current = task;

      task.promise.then(
        () => {
          if (cancelled) return;
          renderTaskRef.current = null;
          try {
            const dataUrl = canvas.toDataURL('image/jpeg', 0.72);
            cache.set(pageNumber, dataUrl);
          } catch {
            // Canvas may be tainted in rare CORS cases; skip cache
          }
          setRendered(true);
          setLoading(false);
        },
        (err) => {
          if (err?.name !== 'RenderingCancelledException') {
            console.warn(`Thumbnail render failed for page ${pageNumber}`, err);
          }
          if (!cancelled) setLoading(false);
        }
      );
    });

    return () => {
      cancelled = true;
      if (renderTaskRef.current) {
        renderTaskRef.current.cancel();
        renderTaskRef.current = null;
      }
    };
  }, [isVisible, pdfDoc, pageNumber, cache]);

  return (
    <button
      type="button"
      ref={containerRef}
      onClick={() => onSelect(pageNumber)}
      className={`relative w-full rounded border p-1 text-left transition-colors ${
        isActive ? 'border-blue-600 ring-2 ring-blue-200 bg-blue-50' : 'border-gray-200 bg-white hover:border-gray-400'
      }`}
      data-testid={`esign-thumb-${pageNumber}`}
    >
      <div
        className="mx-auto flex items-center justify-center bg-gray-100 rounded overflow-hidden"
        style={{ width: THUMB_MAX_WIDTH, minHeight: 72 }}
      >
        {!isVisible && <Skeleton className="h-[72px] w-full" />}
        {isVisible && !rendered && loading && (
          <Skeleton className="h-[72px] w-full" />
        )}
        <canvas
          ref={canvasRef}
          className={`max-w-full h-auto ${isVisible ? 'block' : 'hidden'}`}
          style={{ maxWidth: THUMB_MAX_WIDTH }}
        />
      </div>
      <div className="mt-1 flex items-center justify-center gap-1 text-[11px] font-medium text-gray-700">
        <span>{pageNumber}</span>
        {hasFields && (
          <span
            className="inline-block h-2 w-2 rounded-full bg-amber-500"
            title="Has signature fields"
            aria-label="Has fields"
          />
        )}
      </div>
    </button>
  );
}

export function EsignPdfThumbnailSidebar({
  pdfDoc,
  numPages,
  currentPage,
  fields = [],
  onPageSelect,
}) {
  const scrollRef = useRef(null);
  const [scrollRoot, setScrollRoot] = useState(null);
  const cacheRef = useRef(createThumbnailCache(THUMB_CACHE_MAX));

  const scrollRootRef = useCallback((node) => {
    scrollRef.current = node;
    if (node) setScrollRoot(node);
  }, []);

  const pagesWithFields = useMemo(() => {
    const set = new Set();
    fields.forEach((f) => set.add(f.page_number));
    return set;
  }, [fields]);

  useEffect(() => {
    if (!scrollRoot || !currentPage) return;
    const thumb = scrollRoot.querySelector(`[data-testid="esign-thumb-${currentPage}"]`);
    thumb?.scrollIntoView({ block: 'nearest' });
  }, [currentPage, scrollRoot]);

  if (!pdfDoc || !numPages) {
    return null;
  }

  return (
    <aside
      ref={scrollRootRef}
      className="hidden md:block w-[7.5rem] shrink-0 overflow-y-auto border-r bg-gray-50 p-2 space-y-2 min-h-0"
      data-testid="esign-thumbnail-sidebar"
    >
      {Array.from({ length: numPages }, (_, i) => {
        const pageNumber = i + 1;
        return (
          <EsignPdfThumbnailItem
            key={pageNumber}
            pageNumber={pageNumber}
            pdfDoc={pdfDoc}
            scrollRoot={scrollRoot}
            isActive={currentPage === pageNumber}
            hasFields={pagesWithFields.has(pageNumber)}
            onSelect={onPageSelect}
            cache={cacheRef.current}
          />
        );
      })}
    </aside>
  );
}
