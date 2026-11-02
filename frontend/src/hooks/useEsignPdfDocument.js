import { useState, useEffect } from 'react';
import * as pdfjsLib from 'pdfjs-dist';
import pdfjsWorker from '../pdf-worker-polyfill.js?worker&url';

pdfjsLib.GlobalWorkerOptions.workerSrc = pdfjsWorker;

const DEFAULT_RANGE_CHUNK_SIZE = 65536;

/**
 * Load a PDF for e-sign with byte-range friendly settings (large documents).
 * Does not prefetch every page dimension — pages report size when rendered.
 */
export function useEsignPdfDocument(pdfUrl) {
  const [pdfDoc, setPdfDoc] = useState(null);
  const [numPages, setNumPages] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (!pdfUrl) {
      setPdfDoc(null);
      setNumPages(0);
      setLoading(false);
      setError(null);
      return undefined;
    }

    let isCancelled = false;
    setLoading(true);
    setError(null);

    const headers = {};
    const accessToken = localStorage.getItem('access_token');
    if (accessToken) {
      headers.Authorization = `Bearer ${accessToken}`;
    }

    const loadingTask = pdfjsLib.getDocument({
      url: pdfUrl,
      withCredentials: true,
      httpHeaders: headers,
      disableAutoFetch: true,
      disableStream: false,
      rangeChunkSize: DEFAULT_RANGE_CHUNK_SIZE,
    });

    loadingTask.promise.then(
      (doc) => {
        if (isCancelled) {
          doc.destroy();
          return;
        }
        setPdfDoc(doc);
        setNumPages(doc.numPages);
        setLoading(false);
      },
      (err) => {
        if (!isCancelled) {
          console.error('Failed to load e-sign PDF:', err);
          setError(err);
          setLoading(false);
        }
      }
    );

    return () => {
      isCancelled = true;
      loadingTask.destroy();
    };
  }, [pdfUrl]);

  return { pdfDoc, numPages, loading, error };
}
