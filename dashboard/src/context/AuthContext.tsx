import React, { createContext, useContext, useEffect, useState } from 'react';
import { api, clearStoredApiKey, getStoredApiKey, setOnUnauthorizedCallback, setStoredApiKey } from '../api/client';

interface AuthContextType {
  apiKey: string | null;
  isAuthenticated: boolean;
  authError: string | null;
  login: (key: string) => Promise<boolean>;
  logout: () => void;
  clearAuthError: () => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [apiKey, setApiKey] = useState<string | null>(() => getStoredApiKey());
  const [authError, setAuthError] = useState<string | null>(null);

  useEffect(() => {
    setOnUnauthorizedCallback((msg) => {
      setApiKey(null);
      setAuthError(msg || 'Invalid API Key. Please log in.');
    });
  }, []);

  const login = async (key: string): Promise<boolean> => {
    const trimmed = key.trim();
    if (!trimmed) {
      setAuthError('Please enter an admin API key');
      return false;
    }

    setStoredApiKey(trimmed);
    setApiKey(trimmed);
    setAuthError(null);

    try {
      // Test the key against stats summary or templates
      await api.getTemplates();
      return true;
    } catch (err: any) {
      clearStoredApiKey();
      setApiKey(null);
      setAuthError(err.message || 'Authentication failed: Invalid API key');
      return false;
    }
  };

  const logout = () => {
    clearStoredApiKey();
    setApiKey(null);
    setAuthError(null);
  };

  const clearAuthError = () => setAuthError(null);

  return (
    <AuthContext.Provider
      value={{
        apiKey,
        isAuthenticated: !!apiKey,
        authError,
        login,
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
