import React, { useState } from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider, useAuth } from './context/AuthContext';
import { ToastProvider } from './context/ToastContext';
import { Layout } from './components/layout/Layout';
import { ProtectedRoute, PublicOnlyRoute, SuperAdminRoute, TenantContextRoute } from './components/auth/ProtectedRoutes';
import { LoginPage } from './pages/LoginPage';
import { OverviewPage } from './pages/OverviewPage';
import { EventsPage } from './pages/EventsPage';
import { EmployeesPage } from './pages/EmployeesPage';
import { DigestsPage } from './pages/DigestsPage';
import { TemplatesPage } from './pages/TemplatesPage';
import { SettingsPage } from './pages/SettingsPage';
import { SuperAdminPage } from './pages/SuperAdminPage';
import { AuditLogsPage } from './pages/AuditLogsPage';
import { PhotoUploadPortal } from './pages/PhotoUploadPortal';

const AppRoutes: React.FC = () => {
  const { isSuperAdmin, activeOrg, selectedTenantId } = useAuth();
  const [refreshKey, setRefreshKey] = useState(0);

  const handleRefreshAll = () => {
    setRefreshKey((prev) => prev + 1);
  };

  const tenantKey = `${refreshKey}-${selectedTenantId || activeOrg?.id || 'none'}`;

  return (
    <Routes>
      {/* Public Photo Upload Portal */}
      <Route path="/upload-photo" element={<PhotoUploadPortal />} />

      {/* Public Only Route (Login) */}
      <Route
        path="/login"
        element={
          <PublicOnlyRoute>
            <LoginPage />
          </PublicOnlyRoute>
        }
      />

      {/* Protected Routes inside App Layout */}
      <Route
        element={
          <ProtectedRoute>
            <Layout onRefreshData={handleRefreshAll} />
          </ProtectedRoute>
        }
      >
        <Route
          path="/"
          element={<Navigate to={isSuperAdmin ? '/superadmin/organizations' : '/overview'} replace />}
        />
        <Route element={<TenantContextRoute />}>
          <Route
            path="/overview"
            element={
            <OverviewPage
              key={tenantKey}
              onNavigateTab={() => {}}
              onOpenScanModal={() => {}}
            />
            }
          />
          <Route path="/events" element={<EventsPage key={tenantKey} />} />
          <Route
            path="/employees"
            element={
            <EmployeesPage
              key={tenantKey}
              onNavigateTab={() => {}}
            />
            }
          />
          <Route path="/digests" element={<DigestsPage key={tenantKey} />} />
          <Route path="/templates" element={<TemplatesPage key={tenantKey} />} />
          <Route path="/settings" element={<SettingsPage key={tenantKey} />} />
        </Route>

        {/* SuperAdmin Routes */}
        <Route
          path="/superadmin"
          element={<Navigate to="/superadmin/organizations" replace />}
        />
        <Route
          path="/superadmin/organizations"
          element={
            <SuperAdminRoute>
              <SuperAdminPage />
            </SuperAdminRoute>
          }
        />
        <Route
          path="/superadmin/organizations/:orgId"
          element={
            <SuperAdminRoute>
              <SuperAdminPage />
            </SuperAdminRoute>
          }
        />
        <Route
          path="/superadmin/audit-logs"
          element={
            <SuperAdminRoute>
              <AuditLogsPage />
            </SuperAdminRoute>
          }
        />

        {/* Catch-all fallback */}
        <Route
          path="*"
          element={<Navigate to="/" replace />}
        />
      </Route>
    </Routes>
  );
};

export function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <ToastProvider>
          <AppRoutes />
        </ToastProvider>
      </AuthProvider>
    </BrowserRouter>
  );
}

export default App;
