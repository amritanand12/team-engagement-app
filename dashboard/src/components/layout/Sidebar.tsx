import React from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import {
  LayoutDashboard,
  CalendarCheck,
  Users,
  Mail,
  FileCode,
  RefreshCw,
  Sparkles,
  LogOut,
  Settings as SettingsIcon,
  Crown,
} from 'lucide-react';
import { useAuth } from '../../context/AuthContext';

export type NavTab = 'superadmin' | 'audit' | 'overview' | 'events' | 'employees' | 'digests' | 'templates' | 'settings';

interface SidebarProps {
  onOpenScanModal: () => void;
  onOpenHrmsSync: () => void;
  isMobileOpen: boolean;
  onCloseMobile: () => void;
}

export const Sidebar: React.FC<SidebarProps> = ({
  onOpenScanModal,
  onOpenHrmsSync,
  isMobileOpen,
  onCloseMobile,
}) => {
  const { user, activeOrg, isSuperAdmin, selectedTenantId, logout } = useAuth();
  const location = useLocation();
  const navigate = useNavigate();

  const getActiveTab = (): NavTab => {
    const p = location.pathname;
    if (p.startsWith('/superadmin/audit-logs')) return 'audit';
    if (p.startsWith('/superadmin')) return 'superadmin';
    if (p.startsWith('/events')) return 'events';
    if (p.startsWith('/employees')) return 'employees';
    if (p.startsWith('/digests')) return 'digests';
    if (p.startsWith('/templates')) return 'templates';
    if (p.startsWith('/settings')) return 'settings';
    return 'overview';
  };

  const activeTab = getActiveTab();

  const platformItems = [
    { id: 'superadmin' as NavTab, path: '/superadmin/organizations', label: 'Organizations', icon: Crown },
    { id: 'audit' as NavTab, path: '/superadmin/audit-logs', label: 'Audit Logs', icon: CalendarCheck },
  ];
  const tenantItems = [
    { id: 'overview' as NavTab, path: '/overview', label: 'Overview', icon: LayoutDashboard },
    { id: 'events' as NavTab, path: '/events', label: 'Events Log', icon: CalendarCheck },
    { id: 'employees' as NavTab, path: '/employees', label: 'Employees', icon: Users },
    { id: 'digests' as NavTab, path: '/digests', label: 'Daily Digests', icon: Mail },
    { id: 'templates' as NavTab, path: '/templates', label: 'Templates', icon: FileCode },
    { id: 'settings' as NavTab, path: '/settings', label: 'Settings & Demo', icon: SettingsIcon },
  ];
  const canUseTenantOperations = !isSuperAdmin || Boolean(selectedTenantId);

  const handleNavClick = (path: string) => {
    navigate(path);
    onCloseMobile();
  };

  const handleLogout = () => {
    logout();
    navigate('/login', { replace: true });
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
            <p className="text-xs text-slate-400 font-medium">
              {isSuperAdmin ? 'SuperAdmin Console' : (activeOrg?.name || 'Admin Console')}
            </p>
          </div>
        </div>

        {/* Navigation */}
        <div className="flex-1 px-4 py-6 space-y-1.5 overflow-y-auto">
          {isSuperAdmin && <>
          <div className="px-3 pb-2 text-[11px] font-semibold uppercase tracking-wider text-slate-500">Platform Management</div>
          {platformItems.map((item) => {
            const Icon = item.icon;
            const isActive = activeTab === item.id;
            return (
              <button
                key={item.id}
                type="button"
                onClick={() => handleNavClick(item.path)}
                className={`w-full flex items-center gap-3 px-3.5 py-2.5 rounded-xl text-sm font-medium border transition-colors duration-150 outline-none focus:outline-none focus:ring-0 select-none ${
                  isActive
                    ? 'bg-purple-500/20 text-purple-300 font-semibold border-purple-500/40'
                    : 'border-transparent text-slate-400 hover:text-slate-100 hover:bg-slate-800/60'
                }`}
              >
                <Icon
                  className={`w-4 h-4 ${
                  isActive
                    ? 'text-purple-400'
                      : 'text-slate-400'
                  }`}
                />
                <span>{item.label}</span>
              </button>
            );
          })}
          </>}

          {canUseTenantOperations && <>
          <div className="pt-6 px-3 pb-2 text-[11px] font-semibold uppercase tracking-wider text-slate-500">
            {isSuperAdmin ? 'Tenant Operations' : 'Navigation'}
          </div>
          {tenantItems.map((item) => {
            const Icon = item.icon;
            const isActive = activeTab === item.id;
            return (
              <button key={item.id} type="button" onClick={() => handleNavClick(item.path)}
                className={`w-full flex items-center gap-3 px-3.5 py-2.5 rounded-xl text-sm font-medium border transition-colors duration-150 outline-none select-none ${isActive ? 'bg-rose-500/15 text-rose-400 font-semibold border-rose-500/30' : 'border-transparent text-slate-400 hover:text-slate-100 hover:bg-slate-800/60'}`}>
                <Icon className={`w-4 h-4 ${isActive ? 'text-rose-400' : 'text-slate-400'}`} />
                <span>{item.label}</span>
              </button>
            );
          })}
          </>}

          {/* Quick Ops Actions */}
          {canUseTenantOperations && <>
          <div className="pt-6 px-3 pb-2 text-[11px] font-semibold uppercase tracking-wider text-slate-500">
            Operations
          </div>
          <button
            type="button"
            onClick={() => {
              onOpenScanModal();
              onCloseMobile();
            }}
            className="w-full flex items-center gap-3 px-3.5 py-2.5 rounded-xl text-sm font-medium border border-transparent text-slate-400 hover:text-white hover:bg-slate-800/60 transition-colors duration-150 outline-none focus:outline-none focus:ring-0"
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
            className="w-full flex items-center gap-3 px-3.5 py-2.5 rounded-xl text-sm font-medium border border-transparent text-slate-400 hover:text-white hover:bg-slate-800/60 transition-colors duration-150 outline-none focus:outline-none focus:ring-0"
          >
            <RefreshCw className="w-4 h-4 text-sky-400" />
            <span>Sync with HRMS</span>
          </button>
          </>}
        </div>

        {/* Bottom User / Session */}
        <div className="p-4 border-t border-slate-800 bg-slate-950/60">
          <div className="flex items-center justify-between px-2 py-1.5">
            <div className="flex-1 min-w-0 pr-2">
              <p className="text-xs font-semibold text-white truncate">
                {user?.full_name || 'Admin User'}
              </p>
              <div className="flex items-center gap-1.5 mt-0.5">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 shrink-0" />
                <span className="text-[11px] text-slate-400 truncate">
                  {isSuperAdmin ? 'Platform SuperAdmin' : (user?.email || 'Tenant Session')}
                </span>
              </div>
            </div>
            <button
              type="button"
              onClick={handleLogout}
              className="p-1.5 rounded-lg text-slate-400 hover:text-rose-400 hover:bg-rose-500/10 transition-colors shrink-0"
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

