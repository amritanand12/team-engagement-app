import React from 'react';
import { useLocation } from 'react-router-dom';
import { Menu, Play, RefreshCw, Clock, Crown, Building2 } from 'lucide-react';
import { useAuth } from '../../context/AuthContext';

interface HeaderProps {
  onOpenMobileSidebar: () => void;
  onOpenScanModal: () => void;
  onOpenHrmsSync: () => void;
}

export const Header: React.FC<HeaderProps> = ({
  onOpenMobileSidebar,
  onOpenScanModal,
  onOpenHrmsSync,
}) => {
  const { user, activeOrg, isSuperAdmin } = useAuth();
  const location = useLocation();

  const getTabTitle = () => {
    const p = location.pathname;
    if (p.startsWith('/superadmin')) return 'Platform SuperAdmin Hub';
    if (p.startsWith('/events')) return 'Celebration Events Log';
    if (p.startsWith('/employees')) return 'Employee Profiles Directory';
    if (p.startsWith('/digests')) return 'Team Digest Logs';
    if (p.startsWith('/templates')) return 'Email Templates & Variants';
    if (p.startsWith('/settings')) return 'Organization Settings';
    return 'Operations Overview';
  };

  const todayFormatted = new Intl.DateTimeFormat('en-US', {
    weekday: 'short',
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  }).format(new Date());

  return (
    <header className="sticky top-0 z-30 flex items-center justify-between h-16 px-4 sm:px-8 bg-white/90 backdrop-blur-md border-b border-slate-200">
      <div className="flex items-center gap-3">
        <button
          type="button"
          onClick={onOpenMobileSidebar}
          className="p-2 -ml-2 rounded-xl text-slate-500 hover:text-slate-900 hover:bg-slate-100 lg:hidden"
        >
          <Menu className="w-5 h-5" />
        </button>
        <div className="flex items-center gap-3">
          <h2 className="text-base sm:text-lg font-bold text-slate-800 tracking-tight leading-none">
            {getTabTitle()}
          </h2>

          {/* Org & Role Badge */}
          <div className="hidden sm:flex items-center gap-2">
            {isSuperAdmin ? (
              <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full bg-purple-100 text-purple-800 border border-purple-200 text-[10px] font-extrabold uppercase tracking-wider">
                <Crown className="w-3 h-3 text-purple-600" />
                <span>SuperAdmin</span>
              </span>
            ) : (
              <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full bg-rose-50 text-rose-700 border border-rose-200 text-[10px] font-bold">
                <Building2 className="w-3 h-3 text-rose-500" />
                <span>{activeOrg?.name || 'Tenant Admin'}</span>
              </span>
            )}
          </div>
        </div>
      </div>

      <div className="flex items-center gap-2 sm:gap-3">
        {/* Date Pill */}
        <div className="hidden md:flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-slate-50 border border-slate-200 text-xs font-medium text-slate-600">
          <Clock className="w-3.5 h-3.5 text-slate-400" />
          <span>Today: {todayFormatted}</span>
        </div>

        {/* HRMS Sync Quick Trigger */}
        <button
          type="button"
          onClick={onOpenHrmsSync}
          className="hidden sm:inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl border border-slate-200 bg-white hover:bg-slate-50 text-slate-700 text-xs font-medium transition-colors shadow-xs"
          title="Sync latest employee data from HRMS"
        >
          <RefreshCw className="w-3.5 h-3.5 text-sky-500" />
          <span>Sync HRMS</span>
        </button>

        {/* Primary Run Scan Trigger Button */}
        <button
          type="button"
          onClick={onOpenScanModal}
          className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-xl bg-rose-600 hover:bg-rose-700 text-white text-xs sm:text-sm font-semibold transition-all shadow-sm hover:shadow-rose-600/20 active:scale-98"
        >
          <Play className="w-3.5 h-3.5 fill-current" />
          <span>Run Scan Now</span>
        </button>
      </div>
    </header>
  );
};
