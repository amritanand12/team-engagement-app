import React, { createContext, useContext, useEffect, useState } from 'react';
import {
  api,
  clearStoredApiKey,
  clearStoredAuthToken,
  clearStoredTenantId,
  getStoredApiKey,
  getStoredAuthToken,
  getStoredTenantId,
  setOnUnauthorizedCallback,
  setStoredApiKey,
  setStoredAuthToken,
  setStoredTenantId,
} from '../api/client';
import { Organization, User, UserRole } from '../types';

interface AuthContextType {
  user: User | null;
  activeOrg: Organization | null;
  role: UserRole | null;
  token: string | null;
  apiKey: string | null;
  selectedTenantId: string | null;
  isAuthenticated: boolean;
  isSuperAdmin: boolean;
  authError: string | null;
  loginWithEmail: (email: string, password: string) => Promise<boolean>;
  loginWithApiKey: (key: string) => Promise<boolean>;
  switchTenant: (tenantId: string | null, org?: Organization | null) => void;
  logout: () => void;
  clearAuthError: () => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [token, setToken] = useState<string | null>(() => getStoredAuthToken());
  const [apiKey, setApiKey] = useState<string | null>(() => getStoredApiKey());
  const [selectedTenantId, setSelectedTenantId] = useState<string | null>(() => getStoredTenantId());
  const [user, setUser] = useState<User | null>(null);
  const [activeOrg, setActiveOrg] = useState<Organization | null>(null);
  const [authError, setAuthError] = useState<string | null>(null);
  const [initializing, setInitializing] = useState<boolean>(true);

  const restoreSession = async () => {
    if (token) {
      try {
        const profile = await api.getCurrentProfile();
        setUser(profile.user);
        setActiveOrg(profile.organization);
      } catch (err: any) {
        // Clear invalid tokens
        clearStoredAuthToken();
        clearStoredApiKey();
        setToken(null);
        setApiKey(null);
        setUser(null);
        setActiveOrg(null);
      }
    } else {
      clearStoredApiKey();
      setApiKey(null);
    }
    setInitializing(false);
  };

  useEffect(() => {
    setOnUnauthorizedCallback((msg) => {
      clearStoredAuthToken();
      clearStoredApiKey();
      clearStoredTenantId();
      setToken(null);
      setApiKey(null);
      setUser(null);
      setActiveOrg(null);
      setAuthError(msg || 'Session expired or unauthorized. Please log in.');
    });
    restoreSession();
  }, []);

  const loginWithEmail = async (email: string, password: string): Promise<boolean> => {
    setAuthError(null);
    try {
      const res = await api.loginWithEmail(email, password);
      setStoredAuthToken(res.access_token);
      setToken(res.access_token);
      setUser(res.user);
      setActiveOrg(res.organization);
      if (res.user.role !== 'super_admin') {
        clearStoredTenantId();
        setSelectedTenantId(null);
      }
      return true;
    } catch (err: any) {
      setAuthError(err.message || 'Invalid email or password');
      return false;
    }
  };

  const loginWithApiKey = async (_key: string): Promise<boolean> => {
    setAuthError('API Key web login is disabled in production. Please sign in with your email and password.');
    return false;
  };

  const switchTenant = (tenantId: string | null, org?: Organization | null) => {
    if (tenantId) {
      setStoredTenantId(tenantId);
      setSelectedTenantId(tenantId);
      if (org) setActiveOrg(org);
    } else {
      clearStoredTenantId();
      setSelectedTenantId(null);
      setActiveOrg(null);
    }
  };

  const logout = () => {
    clearStoredAuthToken();
    clearStoredApiKey();
    clearStoredTenantId();
    setToken(null);
    setApiKey(null);
    setSelectedTenantId(null);
    setUser(null);
    setActiveOrg(null);
    setAuthError(null);
  };

  const clearAuthError = () => setAuthError(null);

  if (initializing) {
    return (
      <div className="min-h-screen bg-slate-950 flex items-center justify-center text-slate-400 text-sm">
        <div className="w-8 h-8 border-2 border-rose-500 border-t-transparent rounded-full animate-spin mr-3" />
        Initializing session...
      </div>
    );
  }

  const role = user?.role || null;
  const isSuperAdmin = role === 'super_admin';
  const isAuthenticated = Boolean(token && user);

  return (
    <AuthContext.Provider
      value={{
        user,
        activeOrg,
        role,
        token,
        apiKey: null,
        selectedTenantId,
        isAuthenticated,
        isSuperAdmin,
        authError,
        loginWithEmail,
        loginWithApiKey,
        switchTenant,
        logout,
        clearAuthError,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = (): AuthContextType => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};
