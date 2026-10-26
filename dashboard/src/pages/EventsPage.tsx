import React, { useEffect, useState } from 'react';
import { api } from '../api/client';
import { EventLog } from '../types';
import { Badge } from '../components/common/Badge';
import { Drawer } from '../components/common/Drawer';
import { HtmlPreviewIframe } from '../components/common/HtmlPreviewIframe';
import { EmptyState } from '../components/common/EmptyState';
import { TableSkeleton } from '../components/common/Skeleton';
import { useToast } from '../context/ToastContext';
import {
  CalendarCheck,
  Search,
  RefreshCw,
  RotateCw,
  Eye,
  AlertCircle,
  X,
} from 'lucide-react';


export const EventsPage: React.FC = () => {
  const [events, setEvents] = useState<EventLog[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Filters
  const [batchIdFilter, setBatchIdFilter] = useState<string>('');
  const [statusFilter, setStatusFilter] = useState<string>('');
  const [searchTerm, setSearchTerm] = useState<string>('');

  // Selected event for detail drawer
  const [selectedEvent, setSelectedEvent] = useState<EventLog | null>(null);
  const [isDrawerOpen, setIsDrawerOpen] = useState(false);

  // Resend state tracker: eventId -> boolean
  const [resendingIds, setResendingIds] = useState<Record<string, boolean>>({});

  const toast = useToast();

  const fetchEvents = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.getEvents({
        batch_id: batchIdFilter || undefined,
        status: statusFilter || undefined,
      });
      setEvents(data);
    } catch (err: any) {
      const message = err.message || 'Failed to load events';
      setError(message);
      if (err.status === 403 || err.status === 503) toast.warning('Tenant database needs attention', message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchEvents();
  }, [batchIdFilter, statusFilter]);

  const handleResend = async (eventId: string, e?: React.MouseEvent) => {
    if (e) e.stopPropagation();

    setResendingIds((prev) => ({ ...prev, [eventId]: true }));
    try {
      const res = await api.resendEvent(eventId);
      toast.success('Resend Triggered', res.message);

      // Fetch fresh event detail and update in-place
      const updated = await api.getEvent(eventId);
      setEvents((prev) => prev.map((item) => (item.id === eventId ? updated : item)));
      if (selectedEvent && selectedEvent.id === eventId) {
        setSelectedEvent(updated);
      }
    } catch (err: any) {
      toast.error('Resend Failed', err.message);
    } finally {
      setResendingIds((prev) => ({ ...prev, [eventId]: false }));
    }
  };

  const handleRowClick = (event: EventLog) => {
    setSelectedEvent(event);
    setIsDrawerOpen(true);
  };

  // Client-side text search filter
  const filteredEvents = events.filter((ev) => {
    if (!searchTerm.trim()) return true;
    const term = searchTerm.toLowerCase();
    return (
      (ev.employee_name && ev.employee_name.toLowerCase().includes(term)) ||
      ev.employee_id.toLowerCase().includes(term) ||
      ev.batch_id.toLowerCase().includes(term) ||
      (ev.rendered_subject && ev.rendered_subject.toLowerCase().includes(term))
    );
  });

  const clearAllFilters = () => {
    setBatchIdFilter('');
    setStatusFilter('');
    setSearchTerm('');
  };

  return (
    <div className="space-y-6">
      {/* Header & Filter Controls */}
      <div className="p-5 rounded-2xl bg-white border border-slate-100 shadow-sm space-y-4">
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
          <div>
            <h3 className="text-base font-bold text-slate-800">Celebration Event Logs</h3>
            <p className="text-xs text-slate-500 mt-0.5">
              History of all birthday & anniversary events detected, rendered, and dispatched
            </p>
          </div>
          <button
            type="button"
            onClick={fetchEvents}
            className="inline-flex items-center gap-1.5 px-3.5 py-1.5 rounded-xl border border-slate-200 bg-white hover:bg-slate-50 text-slate-700 text-xs font-semibold shadow-xs transition-colors"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
            <span>Refresh</span>
          </button>
        </div>

        {/* Filter Bar */}
        <div className="grid grid-cols-1 sm:grid-cols-3 lg:grid-cols-4 gap-3 pt-2 border-t border-slate-100">
          {/* Search */}
          <div className="relative">
            <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-slate-400">
              <Search className="w-4 h-4" />
            </div>
            <input
              type="text"
              placeholder="Search employee or subject..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="w-full pl-9 pr-3 py-2 text-xs rounded-xl border border-slate-200 bg-white text-slate-800 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-rose-500/20 focus:border-rose-500"
            />
          </div>

          {/* Batch Date Filter */}
          <div className="relative">
            <input
              type="date"
              value={batchIdFilter}
              onChange={(e) => setBatchIdFilter(e.target.value)}
              className="w-full px-3 py-2 text-xs rounded-xl border border-slate-200 bg-white text-slate-800 focus:outline-none focus:ring-2 focus:ring-rose-500/20 focus:border-rose-500"
              title="Filter by Batch Date"
            />
          </div>

          {/* Status Filter */}
          <div className="relative">
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="w-full px-3 py-2 text-xs rounded-xl border border-slate-200 bg-white text-slate-800 focus:outline-none focus:ring-2 focus:ring-rose-500/20 focus:border-rose-500 cursor-pointer"
            >
              <option value="">All Statuses</option>
              <option value="sent">Sent</option>
              <option value="failed">Failed</option>
              <option value="pending">Pending</option>
              <option value="rendered">Rendered</option>
              <option value="skipped">Skipped</option>
            </select>
          </div>

          {/* Clear Filters Button */}
          {(batchIdFilter || statusFilter || searchTerm) && (
            <div className="flex items-center">
              <button
                type="button"
                onClick={clearAllFilters}
                className="inline-flex items-center gap-1 px-3 py-2 text-xs font-semibold text-rose-600 hover:text-rose-700 hover:bg-rose-50 rounded-xl transition-colors"
              >
                <X className="w-3.5 h-3.5" />
                <span>Reset Filters</span>
              </button>
            </div>
          )}
        </div>
      </div>

      {/* Events Table Container */}
      <div className="rounded-2xl bg-white border border-slate-100 shadow-sm overflow-hidden">
        {loading ? (
          <TableSkeleton rows={8} cols={6} />
        ) : error ? (
          <div className="p-8 text-center text-rose-600 text-xs">
            <AlertCircle className="w-8 h-8 mx-auto mb-2 text-rose-500" />
            <p className="font-semibold">{error}</p>
          </div>
        ) : filteredEvents.length === 0 ? (
          <EmptyState
            icon={CalendarCheck}
            title="No events match your criteria"
            description="No celebration events found for the selected filters. You can trigger a scan or change date filters."
            action={{
              label: 'Clear Filters',
              onClick: clearAllFilters,
            }}
          />
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs text-slate-600">
              <thead className="bg-slate-50/80 border-b border-slate-100 text-[11px] uppercase tracking-wider font-semibold text-slate-500">
                <tr>
                  <th className="px-4 py-3.5">Employee</th>
                  <th className="px-4 py-3.5">Event Type</th>
                  <th className="px-4 py-3.5">Event Date</th>
                  <th className="px-4 py-3.5">Status</th>
                  <th className="px-4 py-3.5">Subject Line</th>
                  <th className="px-4 py-3.5 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {filteredEvents.map((event) => {
                  const isResending = resendingIds[event.id] || false;
                  return (
                    <tr
                      key={event.id}
                      onClick={() => handleRowClick(event)}
                      className="hover:bg-slate-50/80 cursor-pointer transition-colors group"
                    >
                      {/* Employee Name */}
                      <td className="px-4 py-3.5 font-semibold text-slate-800 whitespace-nowrap">
                        <div className="flex items-center gap-2">
                          <span>{event.employee_name || 'Employee Profile'}</span>
                        </div>
                      </td>

                      {/* Event Type & Years */}
                      <td className="px-4 py-3.5 whitespace-nowrap">
                        <div className="flex items-center gap-2">
                          <Badge eventType={event.event_type} />
                          {event.years ? (
                            <span className="text-[11px] font-semibold text-purple-700 bg-purple-100/60 px-1.5 py-0.5 rounded-md">
                              {event.years} yr{event.years > 1 ? 's' : ''}
                            </span>
                          ) : null}
                        </div>
                      </td>

                      {/* Event Date */}
                      <td className="px-4 py-3.5 font-mono text-slate-700 whitespace-nowrap">
                        {event.event_date}
                      </td>

                      {/* Status */}
                      <td className="px-4 py-3.5 whitespace-nowrap">
                        <Badge status={event.status} />
                      </td>

                      {/* Subject Line */}
                      <td className="px-4 py-3.5 max-w-xs truncate text-slate-700">
                        {event.rendered_subject || (
                          <span className="italic text-slate-400">Not rendered yet</span>
                        )}
                      </td>

                      {/* Actions */}
                      <td className="px-4 py-3.5 text-right whitespace-nowrap" onClick={(e) => e.stopPropagation()}>
                        <div className="flex items-center justify-end gap-2">
                          <button
                            type="button"
                            onClick={() => handleRowClick(event)}
                            className="p-1.5 rounded-lg text-slate-400 hover:text-slate-700 hover:bg-slate-100 transition-colors"
                            title="Inspect Details & Preview"
                          >
                            <Eye className="w-4 h-4" />
                          </button>

                          {(event.status === 'failed' || event.status === 'pending') && (
                            <button
                              type="button"
                              onClick={(e) => handleResend(event.id, e)}
                              disabled={isResending}
                              className="inline-flex items-center gap-1 px-2.5 py-1 rounded-lg bg-rose-50 hover:bg-rose-100 text-rose-700 text-[11px] font-semibold border border-rose-200/80 transition-colors disabled:opacity-50"
                              title="Retry render and send"
                            >
                              <RotateCw className={`w-3 h-3 ${isResending ? 'animate-spin' : ''}`} />
                              <span>{isResending ? 'Resending...' : 'Resend'}</span>
                            </button>
                          )}
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Detail & Email Preview Drawer */}
      <Drawer
        isOpen={isDrawerOpen}
        onClose={() => setIsDrawerOpen(false)}
        title={selectedEvent ? `${selectedEvent.employee_name || 'Event'} Celebration` : 'Event Detail'}
        subtitle={selectedEvent ? `Batch Date: ${selectedEvent.batch_id} · ID: ${selectedEvent.id}` : ''}
        width="xl"
      >
        {selectedEvent && (
          <div className="space-y-6">
            {/* Status & Quick Action Banner */}
            <div className="flex items-center justify-between p-4 rounded-xl bg-slate-50 border border-slate-200">
              <div className="flex items-center gap-3">
                <Badge status={selectedEvent.status} size="md" />
                <Badge eventType={selectedEvent.event_type} size="md" />
                {selectedEvent.years && (
                  <span className="text-xs font-bold text-purple-700 bg-purple-100 px-2 py-0.5 rounded-full">
                    {selectedEvent.years} Years Milestone
                  </span>
                )}
              </div>

              {(selectedEvent.status === 'failed' || selectedEvent.status === 'pending') && (
                <button
                  type="button"
                  onClick={() => handleResend(selectedEvent.id)}
                  disabled={resendingIds[selectedEvent.id]}
                  className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-rose-600 hover:bg-rose-700 text-white text-xs font-semibold shadow-xs disabled:opacity-50 transition-colors"
                >
                  <RotateCw className={`w-3.5 h-3.5 ${resendingIds[selectedEvent.id] ? 'animate-spin' : ''}`} />
                  <span>Resend Email</span>
                </button>
              )}
            </div>

            {/* Error Detail Banner if Failed */}
            {selectedEvent.status === 'failed' && (
              <div className="p-4 rounded-xl bg-rose-50 border border-rose-200 text-xs text-rose-900 space-y-1">
                <div className="font-bold flex items-center gap-1.5 text-rose-800">
                  <AlertCircle className="w-4 h-4 text-rose-600" />
                  <span>Delivery / Render Error</span>
                </div>
                <p className="font-mono break-words">{selectedEvent.error_detail || 'Unknown error occurred'}</p>
                <div className="text-[11px] text-rose-700 pt-1">
                  Attempt count: {selectedEvent.attempt_count}
                </div>
              </div>
            )}

            {/* Metadata Grid */}
            <div className="grid grid-cols-2 sm:grid-cols-3 gap-3 text-xs">
              <div className="p-3 rounded-xl bg-slate-50 border border-slate-100">
                <div className="text-slate-400 uppercase text-[10px] font-semibold">Event Date</div>
                <div className="font-semibold text-slate-800 mt-0.5 font-mono">{selectedEvent.event_date}</div>
              </div>
              <div className="p-3 rounded-xl bg-slate-50 border border-slate-100">
                <div className="text-slate-400 uppercase text-[10px] font-semibold">Batch ID</div>
                <div className="font-semibold text-slate-800 mt-0.5 font-mono">{selectedEvent.batch_id}</div>
              </div>
              <div className="p-3 rounded-xl bg-slate-50 border border-slate-100">
                <div className="text-slate-400 uppercase text-[10px] font-semibold">Sent At</div>
                <div className="font-semibold text-slate-800 mt-0.5">
                  {selectedEvent.sent_at ? new Date(selectedEvent.sent_at).toLocaleTimeString() : 'Not sent'}
                </div>
              </div>
            </div>

            {/* Subject Line Preview */}
            <div>
              <label className="block text-xs font-semibold uppercase tracking-wider text-slate-500 mb-1.5">
                Subject Line
              </label>
              <div className="p-3 rounded-xl bg-slate-100 border border-slate-200 text-xs font-medium text-slate-800">
                {selectedEvent.rendered_subject || '— (Not rendered)'}
              </div>
            </div>

            {/* Sandboxed HTML Email Preview */}
            <div>
              <label className="block text-xs font-semibold uppercase tracking-wider text-slate-500 mb-1.5">
                Rendered HTML Preview (Sandboxed iFrame)
              </label>
              <HtmlPreviewIframe
                htmlContent={selectedEvent.rendered_html}
                title={selectedEvent.rendered_subject || 'Email Preview'}
                minHeight="380px"
              />
            </div>
          </div>
        )}
      </Drawer>
    </div>
  );
};
