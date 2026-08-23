import React from 'react';
import { Menu, Play, RefreshCw, Clock } from 'lucide-react';
import { NavTab } from './Sidebar';

interface HeaderProps {
  activeTab: NavTab;
  onOpenMobileSidebar: () => void;
  onOpenScanModal: () => void;
  onOpenHrmsSync: () => void;
}

export const Header: React.FC<HeaderProps> = ({
  activeTab,
  onOpenMobileSidebar,
  onOpenScanModal,
  onOpenHrmsSync,
}) => {
  const getTabTitle = () => {
    switch (activeTab) {
      case 'overview':
        return 'Operations Overview';
      case 'events':
        return 'Celebration Events Log';
      case 'employees':
        return 'Employee Profiles Directory';
      case 'digests':
        return 'Team Digest Logs';
      case 'templates':
        return 'Email Templates & Variants';
      default:
        return 'Dashboard';
    }
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
        <div>
          <h2 className="text-base sm:text-lg font-bold text-slate-800 tracking-tight leading-none">
            {getTabTitle()}
          </h2>
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
