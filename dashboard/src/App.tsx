import React, { useState } from 'react';
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

const AppContent: React.FC = () => {
  const { isAuthenticated } = useAuth();
  const [activeTab, setActiveTab] = useState<NavTab>('overview');
  const [refreshKey, setRefreshKey] = useState(0);

  if (!isAuthenticated) {
    return <LoginPage />;
  }

  const handleRefreshAll = () => {
    setRefreshKey((prev) => prev + 1);
  };

  const renderActivePage = () => {
    switch (activeTab) {
      case 'overview':
        return (
          <OverviewPage
            key={refreshKey}
            onNavigateTab={(tab) => setActiveTab(tab)}
            onOpenScanModal={() => {
              // Triggered via Header / Layout
            }}
          />
        );
      case 'events':
        return <EventsPage key={refreshKey} />;
      case 'employees':
        return <EmployeesPage key={refreshKey} />;
      case 'digests':
        return <DigestsPage key={refreshKey} />;
      case 'templates':
        return <TemplatesPage key={refreshKey} />;
      default:
        return <OverviewPage key={refreshKey} onNavigateTab={(tab) => setActiveTab(tab)} onOpenScanModal={() => {}} />;
    }
  };

  return (
    <Layout
      activeTab={activeTab}
      onSelectTab={(tab) => setActiveTab(tab)}
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
