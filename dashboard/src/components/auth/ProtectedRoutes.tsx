import React from 'react';
import { Navigate, Outlet } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';

export const ProtectedRoute: React.FC<{ children?: React.ReactNode }> = ({ children }) => {
  const { isAuthenticated } = useAuth();

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  return children ? <>{children}</> : <Outlet />;
};

export const SuperAdminRoute: React.FC<{ children?: React.ReactNode }> = ({ children }) => {
  const { isAuthenticated, isSuperAdmin } = useAuth();

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  if (!isSuperAdmin) {
    return <Navigate to="/overview" replace />;
  }

  return children ? <>{children}</> : <Outlet />;
};

export const PublicOnlyRoute: React.FC<{ children?: React.ReactNode }> = ({ children }) => {
  const { isAuthenticated, isSuperAdmin } = useAuth();

  if (isAuthenticated) {
    return <Navigate to={isSuperAdmin ? '/superadmin/organizations' : '/overview'} replace />;
  }

  return children ? <>{children}</> : <Outlet />;
};
