import React, { useEffect, useState } from 'react';
import { api } from '../api/client';
import { DigestLog } from '../types';
import { Badge } from '../components/common/Badge';
import { Drawer } from '../components/common/Drawer';
import { HtmlPreviewIframe } from '../components/common/HtmlPreviewIframe';
import { Pagination } from '../components/common/Pagination';
import { EmptyState } from '../components/common/EmptyState';
import { TableSkeleton } from '../components/common/Skeleton';
import { useToast } from '../context/ToastContext';
import {
  Mail,
  RefreshCw,
  Eye,
  Hash,
  Sparkles,
  AlertCircle,
  Calendar,
} from 'lucide-react';

export const DigestsPage: React.FC = () => {
  const toast = useToast();
  const [digests, setDigests] = useState<DigestLog[]>([]);
  const [total, setTotal] = useState(0);
  const [limit, setLimit] = useState(25);
  const [offset, setOffset] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Selected digest for preview
  const [selectedDigest, setSelectedDigest] = useState<DigestLog | null>(null);
  const [isDrawerOpen, setIsDrawerOpen] = useState(false);

  const fetchDigests = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.getDigests({ limit, offset });
      setDigests(data.items);
      setTotal(data.total);
    } catch (err: any) {
      const message = err.message || 'Failed to load daily digests';
      setError(message);
      if (err.status === 403 || err.status === 503) toast.warning('Tenant database needs attention', message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDigests();
  }, [limit, offset]);

  const handleRowClick = (digest: DigestLog) => {
    setSelectedDigest(digest);
    setIsDrawerOpen(true);
  };

  return (
    <div className="space-y-6">
      {/* Top Header */}
      <div className="p-5 rounded-2xl bg-white border border-slate-100 shadow-sm space-y-2">
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
          <div>
            <h3 className="text-base font-bold text-slate-800">Team Celebration Digests</h3>
            <p className="text-xs text-slate-500 mt-0.5">
              Daily aggregated digest posts dispatched to company-wide channels (merging same-day events)
            </p>
          </div>
          <button
            type="button"
            onClick={fetchDigests}
            className="inline-flex items-center gap-1.5 px-3.5 py-1.5 rounded-xl border border-slate-200 bg-white hover:bg-slate-50 text-slate-700 text-xs font-semibold shadow-xs transition-colors"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
            <span>Refresh</span>
          </button>
        </div>
      </div>

      {/* Digests Table */}
      <div className="rounded-2xl bg-white border border-slate-100 shadow-sm overflow-hidden">
        {loading ? (
          <TableSkeleton rows={6} cols={5} />
        ) : error ? (
          <div className="p-8 text-center text-rose-600 text-xs">
            <AlertCircle className="w-8 h-8 mx-auto mb-2 text-rose-500" />
            <p className="font-semibold">{error}</p>
          </div>
        ) : digests.length === 0 ? (
          <EmptyState
            icon={Mail}
            title="No digest logs recorded"
            description="Daily digests are created automatically during the daily 6am scan. Trigger a manual scan to generate one."
          />
        ) : (
          <>
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs text-slate-600">
                <thead className="bg-slate-50/80 border-b border-slate-100 text-[11px] uppercase tracking-wider font-semibold text-slate-500">
                  <tr>
                    <th className="px-4 py-3.5">Batch Date</th>
                    <th className="px-4 py-3.5">Target Channel</th>
                    <th className="px-4 py-3.5">Status</th>
                    <th className="px-4 py-3.5">Celebrations Count</th>
                    <th className="px-4 py-3.5">Dispatched At</th>
                    <th className="px-4 py-3.5 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {digests.map((digest) => (
                    <tr
                      key={digest.id}
                      onClick={() => handleRowClick(digest)}
                      className="hover:bg-slate-50/80 cursor-pointer transition-colors group"
                    >
                      {/* Batch Date */}
                      <td className="px-4 py-3.5 font-semibold text-slate-800 font-mono whitespace-nowrap">
                        <div className="flex items-center gap-2">
                          <Calendar className="w-4 h-4 text-slate-400" />
                          <span>{digest.batch_id}</span>
                        </div>
                      </td>

                      {/* Channel */}
                      <td className="px-4 py-3.5 whitespace-nowrap">
                        <span className="inline-flex items-center gap-1 font-mono text-slate-700 bg-slate-100 px-2 py-0.5 rounded-md text-[11px]">
                          <Hash className="w-3 h-3 text-slate-400" />
                          <span>{digest.channel_id}</span>
                        </span>
                      </td>

                      {/* Status */}
                      <td className="px-4 py-3.5 whitespace-nowrap">
                        <Badge status={digest.status} />
                      </td>

                      {/* Event Count */}
                      <td className="px-4 py-3.5 whitespace-nowrap">
                        <div className="flex items-center gap-1 font-semibold text-slate-800">
                          <Sparkles className="w-3.5 h-3.5 text-amber-500" />
                          <span>
                            {digest.event_count} celebration{digest.event_count !== 1 ? 's' : ''}
                          </span>
                        </div>
                      </td>

                      {/* Sent At */}
                      <td className="px-4 py-3.5 text-slate-500 whitespace-nowrap">
                        {digest.sent_at ? new Date(digest.sent_at).toLocaleString() : '—'}
                      </td>

                      {/* Actions */}
                      <td className="px-4 py-3.5 text-right whitespace-nowrap" onClick={(e) => e.stopPropagation()}>
                        <button
                          type="button"
                          onClick={() => handleRowClick(digest)}
                          className="p-1.5 rounded-lg text-slate-400 hover:text-slate-700 hover:bg-slate-100 transition-colors"
                          title="Preview Rendered Digest"
                        >
                          <Eye className="w-4 h-4" />
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            <Pagination
              total={total}
              limit={limit}
              offset={offset}
              onPageChange={(newOffset) => setOffset(newOffset)}
              onLimitChange={(newLimit) => {
                setLimit(newLimit);
                setOffset(0);
              }}
            />
          </>
        )}
      </div>

      {/* Digest Preview Drawer */}
      <Drawer
        isOpen={isDrawerOpen}
        onClose={() => setIsDrawerOpen(false)}
        title={selectedDigest ? `Digest for ${selectedDigest.batch_id}` : 'Digest Detail'}
        subtitle={selectedDigest ? `Target: #${selectedDigest.channel_id}` : ''}
        width="xl"
      >
        {selectedDigest && (
          <div className="space-y-6">
            {/* Status Info Card */}
            <div className="flex items-center justify-between p-4 rounded-xl bg-slate-50 border border-slate-200">
              <div className="flex items-center gap-3">
                <Badge status={selectedDigest.status} size="md" />
                <span className="text-xs font-semibold text-slate-700">
                  {selectedDigest.event_count} Person Celebration{selectedDigest.event_count !== 1 ? 's' : ''} Included
                </span>
              </div>
            </div>

            {/* Error Detail if Failed */}
            {selectedDigest.status === 'failed' && (
              <div className="p-4 rounded-xl bg-rose-50 border border-rose-200 text-xs text-rose-900 space-y-1">
                <div className="font-bold flex items-center gap-1.5 text-rose-800">
                  <AlertCircle className="w-4 h-4 text-rose-600" />
                  <span>Digest Dispatch Error</span>
                </div>
                <p className="font-mono">{selectedDigest.error_detail || 'Unknown delivery failure'}</p>
              </div>
            )}

            {/* Metadata Grid */}
            <div className="grid grid-cols-2 sm:grid-cols-3 gap-3 text-xs">
              <div className="p-3 rounded-xl bg-slate-50 border border-slate-100">
                <div className="text-slate-400 uppercase text-[10px] font-semibold">Batch Date</div>
                <div className="font-semibold text-slate-800 mt-0.5 font-mono">{selectedDigest.batch_id}</div>
              </div>
              <div className="p-3 rounded-xl bg-slate-50 border border-slate-100">
                <div className="text-slate-400 uppercase text-[10px] font-semibold">Channel ID</div>
                <div className="font-semibold text-slate-800 mt-0.5 font-mono">#{selectedDigest.channel_id}</div>
              </div>
              <div className="p-3 rounded-xl bg-slate-50 border border-slate-100">
                <div className="text-slate-400 uppercase text-[10px] font-semibold">Created At</div>
                <div className="font-semibold text-slate-800 mt-0.5">
                  {new Date(selectedDigest.created_at).toLocaleTimeString()}
                </div>
              </div>
            </div>

            {/* Sandboxed Digest Preview */}
            <div>
              <label className="block text-xs font-semibold uppercase tracking-wider text-slate-500 mb-1.5">
                Rendered Digest HTML (Sandboxed iFrame)
              </label>
              <HtmlPreviewIframe
                htmlContent={selectedDigest.rendered_html}
                title={`Digest Preview - ${selectedDigest.batch_id}`}
                minHeight="440px"
              />
            </div>
          </div>
        )}
      </Drawer>
    </div>
  );
};
