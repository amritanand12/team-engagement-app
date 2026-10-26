import React, { useEffect, useState } from 'react';
import { RefreshCw, Search } from 'lucide-react';
import { api } from '../api/client';

interface AuditLogItem {
  id: string;
  organization_name: string | null;
  actor_email: string;
  actor_role: string;
  action: string;
  resource_type: string;
  resource_id: string | null;
  details: string | null;
  created_at: string;
}

export const AuditLogsPage: React.FC = () => {
  const [items, setItems] = useState<AuditLogItem[]>([]);
  const [search, setSearch] = useState('');
  const [page, setPage] = useState(0);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const pageSize = 50;

  const loadLogs = async (offset = page * pageSize, term = search.trim()) => {
    setLoading(true);
    setError(null);
    try {
      const result = await api.getAuditLogs({ limit: pageSize, offset, search: term || undefined });
      setItems(result.items);
      setTotal(result.total);
    } catch (err: any) {
      setError(err.message || 'Unable to load audit logs');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { loadLogs(); }, [page]);

  return (
    <div className="space-y-5">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <p className="text-xs font-bold uppercase tracking-wider text-purple-700">Platform Management</p>
          <h1 className="mt-1 text-2xl font-extrabold text-slate-900">Platform Audit Logs</h1>
          <p className="mt-1 text-sm text-slate-500">Administrative actions across the platform and its organizations.</p>
        </div>
        <button type="button" onClick={() => loadLogs()} className="inline-flex items-center gap-2 self-start rounded-lg border border-slate-200 bg-white px-3 py-2 text-xs font-semibold text-slate-700 hover:bg-slate-50">
          <RefreshCw className={`h-3.5 w-3.5 ${loading ? 'animate-spin' : ''}`} /> Refresh
        </button>
      </div>

      <form className="flex gap-2" onSubmit={(event) => { event.preventDefault(); setPage(0); loadLogs(0, search.trim()); }}>
        <div className="relative max-w-lg flex-1">
          <Search className="absolute left-3 top-2.5 h-4 w-4 text-slate-400" />
          <input value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Search actor, action, tenant, or details" className="w-full rounded-lg border border-slate-200 bg-white py-2 pl-9 pr-3 text-sm outline-none focus:border-purple-400" />
        </div>
        <button type="submit" className="rounded-lg bg-slate-900 px-4 py-2 text-xs font-semibold text-white">Search</button>
      </form>

      {error && <div role="alert" className="rounded-lg border border-rose-200 bg-rose-50 p-3 text-sm text-rose-800">{error}</div>}
      <div className="overflow-x-auto rounded-xl border border-slate-200 bg-white shadow-sm">
        <table className="w-full min-w-[850px] text-left text-xs">
          <thead className="bg-slate-50 text-[10px] uppercase tracking-wider text-slate-500">
            <tr><th className="px-4 py-3">Time</th><th className="px-4 py-3">Tenant</th><th className="px-4 py-3">Actor</th><th className="px-4 py-3">Action</th><th className="px-4 py-3">Resource</th><th className="px-4 py-3">Details</th></tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {items.map((item) => <tr key={item.id} className="align-top hover:bg-slate-50">
              <td className="whitespace-nowrap px-4 py-3 text-slate-600">{new Date(item.created_at).toLocaleString()}</td>
              <td className="px-4 py-3 font-medium text-slate-800">{item.organization_name || 'Platform'}</td>
              <td className="px-4 py-3"><div className="font-medium text-slate-800">{item.actor_email}</div><div className="text-[10px] text-slate-500">{item.actor_role}</div></td>
              <td className="px-4 py-3 font-semibold text-slate-800">{item.action}</td>
              <td className="px-4 py-3 text-slate-600">{item.resource_type}{item.resource_id ? ` · ${item.resource_id}` : ''}</td>
              <td className="max-w-sm px-4 py-3 text-slate-600">{item.details || '—'}</td>
            </tr>)}
            {!loading && items.length === 0 && <tr><td colSpan={6} className="px-4 py-10 text-center text-slate-500">No audit entries found.</td></tr>}
            {loading && <tr><td colSpan={6} className="px-4 py-10 text-center text-slate-500">Loading audit logs…</td></tr>}
          </tbody>
        </table>
      </div>
      <div className="flex items-center justify-between text-xs text-slate-500">
        <span>{total === 0 ? 'No entries' : `Showing ${page * pageSize + 1}–${Math.min((page + 1) * pageSize, total)} of ${total}`}</span>
        <div className="flex gap-2">
          <button type="button" disabled={page === 0} onClick={() => setPage((value) => Math.max(0, value - 1))} className="rounded-md border border-slate-200 px-3 py-1.5 disabled:opacity-40">Previous</button>
          <button type="button" disabled={(page + 1) * pageSize >= total} onClick={() => setPage((value) => value + 1)} className="rounded-md border border-slate-200 px-3 py-1.5 disabled:opacity-40">Next</button>
        </div>
      </div>
    </div>
  );
};
