import { useCallback, useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { toast } from 'sonner';
import { getSignatureRequest, getDownloadSignedUrl, getDownloadCertificateUrl } from '../services/esign';
import { useBreadcrumb } from '../components/layout/BreadcrumbProvider';
import { Button } from '../components/ui/Button';

function formatDateTime(value) {
  if (!value) return '—';
  return new Date(value).toLocaleString('en-US', { timeZone: 'Asia/Riyadh' }) + ' (AST)';
}

function flattenEventLog(signers) {
  const events = [];
  for (const signer of signers || []) {
    const name = signer.user?.name || signer.user?.email || 'Signer';
    for (const action of signer.actions || []) {
      events.push({
        id: action.id,
        timestamp: action.timestamp,
        signerName: name,
        action: action.action,
        ip_address: action.ip_address,
        user_agent: action.user_agent,
      });
    }
  }
  return events.sort(
    (a, b) => new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime()
  );
}

export default function SignatureRequestDetailPage() {
  const { requestId } = useParams();
  const [request, setRequest] = useState(null);
  const [loading, setLoading] = useState(true);
  const { setBreadcrumbs } = useBreadcrumb();

  const load = useCallback(async () => {
    try {
      setLoading(true);
      const data = await getSignatureRequest(requestId);
      setRequest(data);
    } catch {
      toast.error('Failed to load signature request');
    } finally {
      setLoading(false);
    }
  }, [requestId]);

  useEffect(() => {
    load();
  }, [load]);

  useEffect(() => {
    if (!request) return;
    setBreadcrumbs([
      { label: 'Signatures', href: '/signatures' },
      { label: request.title || 'Request detail' },
    ]);
  }, [request, setBreadcrumbs]);

  if (loading) {
    return <div className="container mx-auto p-6 text-muted-foreground">Loading…</div>;
  }

  if (!request) {
    return (
      <div className="container mx-auto p-6">
        <p>Signature request not found.</p>
        <Link to="/signatures" className="text-primary underline">
          Back to signatures
        </Link>
      </div>
    );
  }

  const events = flattenEventLog(request.signers);

  return (
    <div className="container mx-auto max-w-5xl p-6 space-y-8">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <Link to="/signatures" className="text-sm text-muted-foreground hover:underline">
            ← Back to signatures
          </Link>
          <h1 className="text-2xl font-bold mt-2">{request.title}</h1>
          <p className="text-sm text-muted-foreground mt-1">
            Status: <span className="font-medium text-foreground">{request.status}</span>
            {request.completed_at && (
              <> · Completed {formatDateTime(request.completed_at)}</>
            )}
          </p>
        </div>
        {request.status === 'completed' && (
          <div className="flex gap-2">
            <Button
              variant="outline"
              onClick={async () => {
                try {
                  const { url } = await getDownloadSignedUrl(request.id);
                  window.open(url, '_blank', 'noopener,noreferrer');
                } catch {
                  toast.error('Download failed');
                }
              }}
            >
              Download signed PDF
            </Button>
            {request.certificate_storage_key && (
              <Button
                variant="outline"
                onClick={async () => {
                  try {
                    const { url } = await getDownloadCertificateUrl(request.id);
                    window.open(url, '_blank', 'noopener,noreferrer');
                  } catch {
                    toast.error('Certificate download failed');
                  }
                }}
              >
                Download certificate
              </Button>
            )}
          </div>
        )}
      </div>

      <section className="rounded-lg border p-4 space-y-2">
        <h2 className="text-lg font-semibold">Document integrity</h2>
        <dl className="grid gap-2 text-sm">
          <div>
            <dt className="text-muted-foreground">Original document hash</dt>
            <dd className="font-mono text-xs break-all">{request.original_document_hash || '—'}</dd>
          </div>
          <div>
            <dt className="text-muted-foreground">Signed document hash</dt>
            <dd className="font-mono text-xs break-all">{request.signed_document_hash || '—'}</dd>
          </div>
        </dl>
      </section>

      <section className="rounded-lg border p-4">
        <h2 className="text-lg font-semibold mb-3">Signers</h2>
        <div className="overflow-x-auto">
          <table className="min-w-full text-sm border-collapse">
            <thead>
              <tr className="border-b text-left text-muted-foreground">
                <th className="py-2 pr-3">Name</th>
                <th className="py-2 pr-3">Email</th>
                <th className="py-2 pr-3">Signed at (AST)</th>
                <th className="py-2 pr-3">IP address</th>
                <th className="py-2 pr-3">User agent</th>
                <th className="py-2">OTP verified (AST)</th>
              </tr>
            </thead>
            <tbody>
              {(request.signers || []).map((signer) => (
                <tr key={signer.id} className="border-b align-top">
                  <td className="py-2 pr-3">{signer.user?.name || '—'}</td>
                  <td className="py-2 pr-3 break-all">{signer.user?.email || '—'}</td>
                  <td className="py-2 pr-3 whitespace-nowrap">{formatDateTime(signer.signed_at)}</td>
                  <td className="py-2 pr-3 font-mono text-xs">{signer.ip_address || '—'}</td>
                  <td className="py-2 pr-3 max-w-xs break-words text-xs">{signer.user_agent || '—'}</td>
                  <td className="py-2 whitespace-nowrap">{formatDateTime(signer.otp_verified_at)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <section className="rounded-lg border p-4">
        <h2 className="text-lg font-semibold mb-3">Event log</h2>
        {events.length === 0 ? (
          <p className="text-sm text-muted-foreground">No events recorded yet.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="min-w-full text-sm border-collapse">
              <thead>
                <tr className="border-b text-left text-muted-foreground">
                  <th className="py-2 pr-3">Timestamp (AST)</th>
                  <th className="py-2 pr-3">Signer</th>
                  <th className="py-2 pr-3">Action</th>
                  <th className="py-2 pr-3">IP</th>
                  <th className="py-2">User agent</th>
                </tr>
              </thead>
              <tbody>
                {events.map((event) => (
                  <tr key={event.id} className="border-b align-top">
                    <td className="py-2 pr-3 whitespace-nowrap">{formatDateTime(event.timestamp)}</td>
                    <td className="py-2 pr-3">{event.signerName}</td>
                    <td className="py-2 pr-3">{event.action}</td>
                    <td className="py-2 pr-3 font-mono text-xs">{event.ip_address || '—'}</td>
                    <td className="py-2 max-w-md break-words text-xs">{event.user_agent || '—'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </div>
  );
}
