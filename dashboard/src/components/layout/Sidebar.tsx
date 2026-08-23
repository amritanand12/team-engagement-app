import React from 'react';
import {
  LayoutDashboard,
  CalendarCheck,
  Users,
  Mail,
  FileCode,
  RefreshCw,
  Sparkles,
  LogOut,
} from 'lucide-react';
import { useAuth } from '../../context/AuthContext';

export type NavTab = 'overview' | 'events' | 'employees' | 'digests' | 'templates';

interface SidebarProps {
  activeTab: NavTab;
  onSelectTab: (tab: NavTab) => void;
  onOpenScanModal: () => void;
  onOpenHrmsSync: () => void;
  isMobileOpen: boolean;
  onCloseMobile: () => void;
}

export const Sidebar: React.FC<SidebarProps> = ({
  activeTab,
  onSelectTab,
  onOpenScanModal,
  onOpenHrmsSync,
  isMobileOpen,
  onCloseMobile,
}) => {
  const { logout } = useAuth();

  const navItems = [
    { id: 'overview' as NavTab, label: 'Overview', icon: LayoutDashboard },
    { id: 'events' as NavTab, label: 'Events Log', icon: CalendarCheck },
    { id: 'employees' as NavTab, label: 'Employees', icon: Users },
    { id: 'digests' as NavTab, label: 'Daily Digests', icon: Mail },
    { id: 'templates' as NavTab, label: 'Templates', icon: FileCode },
  ];

  const handleNavClick = (tab: NavTab) => {
    onSelectTab(tab);
    onCloseMobile();
  };

  return (
    <>
      {/* Mobile Backdrop */}
      {isMobileOpen && (
        <div
          className="fixed inset-0 bg-slate-900/50 backdrop-blur-xs z-40 lg:hidden"
          onClick={onCloseMobile}
        />
      )}

      <aside
        className={`fixed top-0 bottom-0 left-0 z-50 w-64 bg-slate-900 text-slate-300 flex flex-col border-r border-slate-800 transition-transform duration-300 ease-in-out lg:translate-x-0 ${
          isMobileOpen ? 'translate-x-0' : '-translate-x-full'
        }`}
      >
        {/* Brand */}
        <div className="flex items-center gap-3 px-6 py-5 border-b border-slate-800">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-rose-500 to-pink-500 flex items-center justify-center text-white shadow-md shadow-rose-500/20">
            <Sparkles className="w-5 h-5" />
          </div>
          <div>
            <h1 className="text-base font-bold text-white tracking-tight">Team Engagement</h1>
            <p className="text-xs text-slate-400 font-medium">Admin Ops Console</p>
          </div>
        </div>

        {/* Navigation */}
        <div className="flex-1 px-4 py-6 space-y-1.5 overflow-y-auto">
          <div className="px-3 pb-2 text-[11px] font-semibold uppercase tracking-wider text-slate-500">
            Navigation
          </div>
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive = activeTab === item.id;
            return (
              <button
                key={item.id}
                type="button"
                onClick={() => handleNavClick(item.id)}
                className={`w-full flex items-center gap-3 px-3.5 py-2.5 rounded-xl text-sm font-medium transition-all ${
                  isActive
                    ? 'bg-rose-500/15 text-rose-400 font-semibold shadow-inner border border-rose-500/30'
                    : 'text-slate-400 hover:text-slate-100 hover:bg-slate-800/60'
                }`}
              >
                <Icon className={`w-4 h-4 ${isActive ? 'text-rose-400' : 'text-slate-400'}`} />
                <span>{item.label}</span>
              </button>
            );
          })}

          {/* Quick Ops Actions */}
          <div className="pt-6 px-3 pb-2 text-[11px] font-semibold uppercase tracking-wider text-slate-500">
            Operations
          </div>
          <button
            type="button"
            onClick={() => {
              onOpenScanModal();
              onCloseMobile();
            }}
            className="w-full flex items-center gap-3 px-3.5 py-2.5 rounded-xl text-sm font-medium text-slate-400 hover:text-white hover:bg-slate-800/60 transition-colors"
          >
            <CalendarCheck className="w-4 h-4 text-emerald-400" />
            <span>Run Scan Now</span>
          </button>
          <button
            type="button"
            onClick={() => {
              onOpenHrmsSync();
              onCloseMobile();
            }}
            className="w-full flex items-center gap-3 px-3.5 py-2.5 rounded-xl text-sm font-medium text-slate-400 hover:text-white hover:bg-slate-800/60 transition-colors"
          >
            <RefreshCw className="w-4 h-4 text-sky-400" />
            <span>Sync with HRMS</span>
          </button>
        </div>

        {/* Bottom User / Session */}
        <div className="p-4 border-t border-slate-800 bg-slate-950/40">
          <div className="flex items-center justify-between px-2 py-1.5">
            <div className="flex items-center gap-2 text-xs text-slate-400">
              <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
              <span>Admin Session Active</span>
            </div>
            <button
              type="button"
              onClick={logout}
              className="p-1.5 rounded-lg text-slate-400 hover:text-rose-400 hover:bg-rose-500/10 transition-colors"
              title="End Session (Logout)"
            >
              <LogOut className="w-4 h-4" />
            </button>
          </div>
        </div>
      </aside>
    </>
  );
};
