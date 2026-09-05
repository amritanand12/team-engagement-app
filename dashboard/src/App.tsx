import React, { useState, useEffect, useRef } from 'react';
import { AuthProvider, useAuth } from './context/AuthContext';
import { ToastProvider } from './context/ToastContext';
import { Layout } from './components/layout/Layout';
import { NavTab } from './components/layout/Sidebar';
import { LoginPage } from './pages/LoginPage';
import { OverviewPage } from './pages/OverviewPage';
import { EventsPage } from './pages/EventsPage';
import { EmployeesPage } from './pages/EmployeesPage';
import { DigestsPage } from './pages/DigestsPage';
import { TemplatesPage } from './pages/TemplatesPage';
import { SettingsPage } from './pages/SettingsPage';
import { SuperAdminPage } from './pages/SuperAdminPage';

const AppContent: React.FC = () => {
  const { isAuthenticated, isSuperAdmin, user, activeOrg, selectedTenantId } = useAuth();
  const [activeTab, setActiveTab] = useState<NavTab>(() => (isSuperAdmin ? 'superadmin' : 'overview'));
  const [refreshKey, setRefreshKey] = useState(0);
  const prevUserIdRef = useRef<string | null>(null);

  // Automatically navigate SuperAdmin to 'superadmin' (Platform Hub)
  // and Org Admin to 'overview' upon login or session restore
  useEffect(() => {
    if (user && user.id !== prevUserIdRef.current) {
      prevUserIdRef.current = user.id;
      if (isSuperAdmin) {
        setActiveTab('superadmin');
      } else {
        setActiveTab('overview');
      }
    } else if (!user) {
      prevUserIdRef.current = null;
    }
  }, [user, isSuperAdmin]);

  // Strictly enforce role-based tab isolation
  useEffect(() => {
    if (!isSuperAdmin && activeTab === 'superadmin') {
      setActiveTab('overview');
    }
  }, [isSuperAdmin, activeTab]);

  if (!isAuthenticated) {
    return <LoginPage />;
  }

  const handleRefreshAll = () => {
    setRefreshKey((prev) => prev + 1);
  };

  const tenantKey = `${refreshKey}-${selectedTenantId || activeOrg?.id || 'none'}`;

  const renderActivePage = () => {
    switch (activeTab) {
      case 'superadmin':
        if (!isSuperAdmin) {
          return (
            <OverviewPage
              key={tenantKey}
              onNavigateTab={(tab) => setActiveTab(tab)}
              onOpenScanModal={() => {}}
            />
          );
        }
        return (
          <SuperAdminPage
            key={refreshKey}
            onSwitchToTenant={() => setActiveTab('overview')}
          />
        );
      case 'overview':
        return (
          <OverviewPage
            key={tenantKey}
            onNavigateTab={(tab) => setActiveTab(tab)}
            onOpenScanModal={() => {
              // Triggered via Header / Layout
            }}
          />
        );
      case 'events':
        return <EventsPage key={tenantKey} />;
      case 'employees':
        return <EmployeesPage key={tenantKey} />;
      case 'digests':
        return <DigestsPage key={tenantKey} />;
      case 'templates':
        return <TemplatesPage key={tenantKey} />;
      case 'settings':
        return <SettingsPage key={tenantKey} />;
      default:
        return <OverviewPage key={tenantKey} onNavigateTab={(tab) => setActiveTab(tab)} onOpenScanModal={() => {}} />;
    }
  };

  return (
    <Layout
      activeTab={activeTab}
      onSelectTab={(tab) => {
        if (tab === 'superadmin' && !isSuperAdmin) {
          setActiveTab('overview');
        } else {
          setActiveTab(tab);
        }
      }}
      onRefreshData={handleRefreshAll}
    >
      {renderActivePage()}
    </Layout>
  );
};

export function App() {
  return (
    <AuthProvider>
      <ToastProvider>
        <AppContent />
      </ToastProvider>
    </AuthProvider>
  );
}

export default App;
