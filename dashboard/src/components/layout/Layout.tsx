import React, { useState } from 'react';
import { Outlet } from 'react-router-dom';
import { Sidebar } from './Sidebar';
import { Header } from './Header';
import { Modal } from '../common/Modal';
import { api } from '../../api/client';
import { useToast } from '../../context/ToastContext';
import { ScanTriggerResponse, HrmsSyncResponse } from '../../types';
import { Play, RefreshCw, CheckCircle2 } from 'lucide-react';

interface LayoutProps {
  children?: React.ReactNode;
  onRefreshData?: () => void;
}

export const Layout: React.FC<LayoutProps> = ({
  children,
  onRefreshData,
}) => {
  const [isMobileSidebarOpen, setIsMobileSidebarOpen] = useState(false);
  const [isScanModalOpen, setIsScanModalOpen] = useState(false);
  const [isHrmsModalOpen, setIsHrmsModalOpen] = useState(false);

  // Scan execution state
  const [scanDate, setScanDate] = useState(() => new Date().toISOString().split('T')[0]);
  const [isScanning, setIsScanning] = useState(false);
  const [scanResult, setScanResult] = useState<ScanTriggerResponse | null>(null);

  // HRMS sync execution state
  const [isSyncing, setIsSyncing] = useState(false);
  const [syncResult, setSyncResult] = useState<HrmsSyncResponse | null>(null);

  const toast = useToast();

  const handleRunScan = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsScanning(true);
    setScanResult(null);

    try {
      const res = await api.triggerScan(scanDate);
      setScanResult(res);
      toast.success(
        `Scan executed for ${res.batch_id}`,
        `Detected: ${res.detected}, Rendered: ${res.rendered}, Sent: ${res.sent}, Failed: ${res.failed}, Digest: ${res.digest_status}`
      );
      if (onRefreshData) onRefreshData();
    } catch (err: any) {
      toast.error('Scan Trigger Failed', err.message);
    } finally {
      setIsScanning(false);
    }
  };

  const handleRunHrmsSync = async () => {
    setIsSyncing(true);
    setSyncResult(null);

    try {
      const res = await api.triggerHrmsSync();
      setSyncResult(res);
      toast.success('HRMS Sync Complete', res.message);
      if (onRefreshData) onRefreshData();
    } catch (err: any) {
      toast.error('HRMS Sync Failed', err.message);
    } finally {
      setIsSyncing(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-50 flex">
      {/* Sidebar */}
      <Sidebar
        onOpenScanModal={() => {
          setScanResult(null);
          setIsScanModalOpen(true);
        }}
        onOpenHrmsSync={() => {
          setSyncResult(null);
          setIsHrmsModalOpen(true);
        }}
        isMobileOpen={isMobileSidebarOpen}
        onCloseMobile={() => setIsMobileSidebarOpen(false)}
      />

      {/* Main Content Area */}
      <div className="flex-1 flex flex-col lg:pl-64 min-w-0">
        <Header
          onOpenMobileSidebar={() => setIsMobileSidebarOpen(true)}
          onOpenScanModal={() => {
            setScanResult(null);
            setIsScanModalOpen(true);
          }}
          onOpenHrmsSync={() => {
            setSyncResult(null);
            setIsHrmsModalOpen(true);
          }}
        />

        <main className="flex-1 p-4 sm:p-6 lg:p-8 max-w-7xl w-full mx-auto">{children || <Outlet />}</main>
      </div>

      {/* Run Scan Modal */}
      <Modal
        isOpen={isScanModalOpen}
        onClose={() => setIsScanModalOpen(false)}
        title="Trigger Daily Scan Pipeline"
        subtitle="Manually runs Scan → Render → Send Individual Emails → Digest Pipeline"
        maxWidth="lg"
      >
        <form onSubmit={handleRunScan} className="space-y-4">
          <div>
            <label className="block text-xs font-semibold uppercase tracking-wider text-slate-700 mb-1.5">
              Target Scan Date
            </label>
            <input
              type="date"
              value={scanDate}
              onChange={(e) => setScanDate(e.target.value)}
              required
              className="w-full px-3.5 py-2 rounded-xl border border-slate-200 bg-white text-slate-800 text-sm focus:outline-none focus:ring-2 focus:ring-rose-500/20 focus:border-rose-500"
            />
            <p className="text-xs text-slate-500 mt-1">
              Defaults to today. You can pick past dates to backfill or re-run failed days safely.
            </p>
          </div>

          <div className="p-3.5 rounded-xl bg-amber-50/80 border border-amber-200 text-xs text-amber-900 leading-relaxed">
            <span className="font-semibold">Idempotency Guarantee:</span> Re-running the pipeline will
            never double-send emails that were already sent. It will only render new events and retry failed ones.
          </div>

          {/* Results Summary Box if returned */}
          {scanResult && (
            <div className="p-4 rounded-xl bg-emerald-50 border border-emerald-200 space-y-2">
              <div className="flex items-center gap-2 text-emerald-900 font-semibold text-sm">
                <CheckCircle2 className="w-4 h-4 text-emerald-600" />
                <span>Execution Succeeded for Batch {scanResult.batch_id}</span>
              </div>
              <div className="grid grid-cols-3 sm:grid-cols-5 gap-2 text-center pt-2">
                <div className="p-2 rounded-lg bg-white/80 border border-emerald-100">
                  <div className="text-base font-bold text-slate-800">{scanResult.detected}</div>
                  <div className="text-[10px] text-slate-500 uppercase">Detected</div>
                </div>
                <div className="p-2 rounded-lg bg-white/80 border border-emerald-100">
                  <div className="text-base font-bold text-sky-600">{scanResult.rendered}</div>
                  <div className="text-[10px] text-slate-500 uppercase">Rendered</div>
                </div>
                <div className="p-2 rounded-lg bg-white/80 border border-emerald-100">
                  <div className="text-base font-bold text-emerald-600">{scanResult.sent}</div>
                  <div className="text-[10px] text-slate-500 uppercase">Sent</div>
                </div>
                <div className="p-2 rounded-lg bg-white/80 border border-emerald-100">
                  <div className="text-base font-bold text-rose-600">{scanResult.failed}</div>
                  <div className="text-[10px] text-slate-500 uppercase">Failed</div>
                </div>
                <div className="p-2 rounded-lg bg-white/80 border border-emerald-100">
                  <div className="text-xs font-bold text-purple-600 capitalize truncate mt-1">
                    {scanResult.digest_status}
                  </div>
                  <div className="text-[10px] text-slate-500 uppercase">Digest</div>
                </div>
              </div>
            </div>
          )}

          <div className="flex items-center justify-end gap-3 pt-3">
            <button
              type="button"
              onClick={() => setIsScanModalOpen(false)}
              className="px-4 py-2 rounded-xl text-xs font-semibold text-slate-600 hover:bg-slate-100 transition-colors"
            >
              Close
            </button>
            <button
              type="submit"
              disabled={isScanning}
              className="inline-flex items-center gap-2 px-5 py-2 rounded-xl bg-rose-600 hover:bg-rose-700 disabled:opacity-50 text-white text-xs font-semibold transition-all shadow-sm active:scale-98"
            >
              {isScanning ? (
                <>
                  <div className="w-3.5 h-3.5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                  <span>Running Pipeline...</span>
                </>
              ) : (
                <>
                  <Play className="w-3.5 h-3.5 fill-current" />
                  <span>Execute Pipeline</span>
                </>
              )}
            </button>
          </div>
        </form>
      </Modal>

      {/* HRMS Sync Modal */}
      <Modal
        isOpen={isHrmsModalOpen}
        onClose={() => setIsHrmsModalOpen(false)}
        title="Sync HRMS Employee Mirror"
        subtitle="Fetches latest active employees from HRMS into local EmployeeProfile database table"
        maxWidth="md"
      >
        <div className="space-y-4">
          <p className="text-xs text-slate-600 leading-relaxed">
            The service maintains a local read-only mirror of HRMS data so that daily automated scans do not
            depend on HRMS API uptime at 6am. Triggering this will upsert any new or modified employee records.
          </p>

          {syncResult && (
            <div className="p-4 rounded-xl bg-sky-50 border border-sky-200 text-xs text-sky-900 space-y-1">
              <div className="font-semibold text-sm flex items-center gap-1.5 text-sky-800">
                <CheckCircle2 className="w-4 h-4 text-sky-600" />
                <span>Sync Finished</span>
              </div>
              <p>{syncResult.message}</p>
            </div>
          )}

          <div className="flex items-center justify-end gap-3 pt-3">
            <button
              type="button"
              onClick={() => setIsHrmsModalOpen(false)}
              className="px-4 py-2 rounded-xl text-xs font-semibold text-slate-600 hover:bg-slate-100 transition-colors"
            >
              Close
            </button>
            <button
              type="button"
              onClick={handleRunHrmsSync}
              disabled={isSyncing}
              className="inline-flex items-center gap-2 px-5 py-2 rounded-xl bg-slate-900 hover:bg-slate-800 disabled:opacity-50 text-white text-xs font-semibold transition-all shadow-sm active:scale-98"
            >
              {isSyncing ? (
                <>
                  <div className="w-3.5 h-3.5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                  <span>Syncing...</span>
                </>
              ) : (
                <>
                  <RefreshCw className="w-3.5 h-3.5 text-sky-400" />
                  <span>Trigger HRMS Sync Now</span>
                </>
              )}
            </button>
          </div>
        </div>
      </Modal>
    </div>
  );
};
