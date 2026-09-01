import React, { useState } from 'react';
import { useAuth } from '../context/AuthContext';
import {
  Sparkles,
  Key,
  Mail,
  Lock,
  AlertCircle,
  ArrowRight,
  ShieldCheck,
  Building2,
  Crown,
} from 'lucide-react';

export const LoginPage: React.FC = () => {
  const { loginWithEmail, loginWithApiKey, authError, clearAuthError } = useAuth();

  const [authMode, setAuthMode] = useState<'password' | 'apikey'>('password');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [apiKeyInput, setApiKeyInput] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handlePasswordLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!email.trim() || !password.trim()) return;

    setIsSubmitting(true);
    await loginWithEmail(email, password);
    setIsSubmitting(false);
  };

  const handleApiKeyLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!apiKeyInput.trim()) return;

    setIsSubmitting(true);
    await loginWithApiKey(apiKeyInput);
    setIsSubmitting(false);
  };

  const quickFillSuperAdmin = () => {
    setAuthMode('password');
    setEmail('admin@platform.local');
    setPassword('admin123');
    clearAuthError();
  };

  const quickFillTenantAdmin = () => {
    setAuthMode('password');
    setEmail('admin@acme.com');
    setPassword('acme123');
    clearAuthError();
  };

  return (
    <div className="min-h-screen bg-slate-950 flex flex-col justify-center items-center px-4 sm:px-6 lg:px-8 relative overflow-hidden">
      {/* Background Ambient Glows */}
      <div className="absolute top-1/4 -left-20 w-96 h-96 bg-rose-500/10 rounded-full blur-3xl pointer-events-none" />
      <div className="absolute bottom-1/4 -right-20 w-96 h-96 bg-purple-500/10 rounded-full blur-3xl pointer-events-none" />

      <div className="max-w-md w-full space-y-6 relative z-10">
        {/* Header Branding */}
        <div className="text-center space-y-2">
          <div className="inline-flex items-center justify-center w-14 h-14 rounded-2xl bg-gradient-to-tr from-rose-500 to-pink-500 text-white shadow-xl shadow-rose-500/20 mb-2">
            <Sparkles className="w-7 h-7" />
          </div>
          <h2 className="text-2xl sm:text-3xl font-extrabold text-white tracking-tight">
            Team Engagement Service
          </h2>
          <p className="text-xs text-slate-400 font-medium">
            Multi-Tenant Automated Milestone Celebrations
          </p>
        </div>

        {/* Login Card */}
        <div className="bg-slate-900/90 border border-slate-800 rounded-3xl p-6 sm:p-8 shadow-2xl backdrop-blur-xl space-y-6">
          {/* Tab Selector */}
          <div className="grid grid-cols-2 p-1 bg-slate-950 rounded-2xl border border-slate-800/80 text-xs font-semibold">
            <button
              type="button"
              onClick={() => {
                setAuthMode('password');
                clearAuthError();
              }}
              className={`py-2 px-3 rounded-xl transition-all ${
                authMode === 'password'
                  ? 'bg-rose-600 text-white shadow-md'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              Email & Password
            </button>
            <button
              type="button"
              onClick={() => {
                setAuthMode('apikey');
                clearAuthError();
              }}
              className={`py-2 px-3 rounded-xl transition-all ${
                authMode === 'apikey'
                  ? 'bg-rose-600 text-white shadow-md'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              API Key / Demo
            </button>
          </div>

          {authError && (
            <div className="flex items-start gap-3 p-3.5 rounded-xl bg-rose-500/10 border border-rose-500/30 text-rose-300 text-xs">
              <AlertCircle className="w-4 h-4 text-rose-400 shrink-0 mt-0.5" />
              <div className="flex-1 min-w-0">
                <span className="font-semibold block">Authentication Failed</span>
                <span className="opacity-90">{authError}</span>
              </div>
            </div>
          )}

          {authMode === 'password' ? (
            /* Email & Password Form */
            <form onSubmit={handlePasswordLogin} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold uppercase tracking-wider text-slate-300 mb-1.5">
                  Email Address
                </label>
                <div className="relative">
                  <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-slate-500">
                    <Mail className="w-4 h-4" />
                  </div>
                  <input
                    type="email"
                    required
                    value={email}
                    onChange={(e) => {
                      if (authError) clearAuthError();
                      setEmail(e.target.value);
                    }}
                    placeholder="admin@yourcompany.com"
                    className="w-full pl-10 pr-4 py-2.5 rounded-xl border border-slate-700 bg-slate-950 text-white placeholder-slate-500 text-xs focus:outline-none focus:ring-2 focus:ring-rose-500 focus:border-rose-500 transition-all"
                  />
                </div>
              </div>

              <div>
                <label className="block text-xs font-semibold uppercase tracking-wider text-slate-300 mb-1.5">
                  Password
                </label>
                <div className="relative">
                  <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-slate-500">
                    <Lock className="w-4 h-4" />
                  </div>
                  <input
                    type="password"
                    required
                    value={password}
                    onChange={(e) => {
                      if (authError) clearAuthError();
                      setPassword(e.target.value);
                    }}
                    placeholder="••••••••"
                    className="w-full pl-10 pr-4 py-2.5 rounded-xl border border-slate-700 bg-slate-950 text-white placeholder-slate-500 text-xs focus:outline-none focus:ring-2 focus:ring-rose-500 focus:border-rose-500 transition-all"
                  />
                </div>
              </div>

              <button
                type="submit"
                disabled={isSubmitting || !email.trim() || !password.trim()}
                className="w-full flex items-center justify-center gap-2 py-2.5 px-4 rounded-xl text-xs font-semibold text-white bg-rose-600 hover:bg-rose-500 disabled:opacity-50 disabled:cursor-not-allowed transition-all shadow-lg shadow-rose-600/20 active:scale-98"
              >
                {isSubmitting ? (
                  <>
                    <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                    <span>Signing in...</span>
                  </>
                ) : (
                  <>
                    <span>Sign In to Console</span>
                    <ArrowRight className="w-4 h-4" />
                  </>
                )}
              </button>
            </form>
          ) : (
            /* API Key Form */
            <form onSubmit={handleApiKeyLogin} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold uppercase tracking-wider text-slate-300 mb-1.5">
                  Organization API Key (<code className="text-rose-400 lowercase">x-api-key</code>)
                </label>
                <div className="relative">
                  <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-slate-500">
                    <Key className="w-4 h-4" />
                  </div>
                  <input
                    type="password"
                    required
                    value={apiKeyInput}
                    onChange={(e) => {
                      if (authError) clearAuthError();
                      setApiKeyInput(e.target.value);
                    }}
                    placeholder="Enter Organization API Key..."
                    className="w-full pl-10 pr-4 py-2.5 rounded-xl border border-slate-700 bg-slate-950 text-white placeholder-slate-500 text-xs focus:outline-none focus:ring-2 focus:ring-rose-500 focus:border-rose-500 transition-all font-mono"
                  />
                </div>
              </div>

              <button
                type="submit"
                disabled={isSubmitting || !apiKeyInput.trim()}
                className="w-full flex items-center justify-center gap-2 py-2.5 px-4 rounded-xl text-xs font-semibold text-white bg-rose-600 hover:bg-rose-500 disabled:opacity-50 disabled:cursor-not-allowed transition-all shadow-lg shadow-rose-600/20 active:scale-98"
              >
                {isSubmitting ? (
                  <>
                    <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                    <span>Validating Key...</span>
                  </>
                ) : (
                  <>
                    <span>Enter via API Key</span>
                    <ArrowRight className="w-4 h-4" />
                  </>
                )}
              </button>
            </form>
          )}

          {/* Quick Demo Credentials */}
          <div className="space-y-2 pt-2 border-t border-slate-800">
            <p className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider text-center">
              Quick 1-Click Role Testing
            </p>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
              <button
                type="button"
                onClick={quickFillSuperAdmin}
                className="flex items-center justify-center gap-1.5 p-2 rounded-xl border border-purple-500/30 bg-purple-500/10 hover:bg-purple-500/20 text-purple-300 text-xs font-medium transition-colors text-left"
              >
                <Crown className="w-3.5 h-3.5 text-purple-400 shrink-0" />
                <span>SuperAdmin Demo</span>
              </button>

              <button
                type="button"
                onClick={quickFillTenantAdmin}
                className="flex items-center justify-center gap-1.5 p-2 rounded-xl border border-rose-500/30 bg-rose-500/10 hover:bg-rose-500/20 text-rose-300 text-xs font-medium transition-colors text-left"
              >
                <Building2 className="w-3.5 h-3.5 text-rose-400 shrink-0" />
                <span>Tenant Admin (Acme)</span>
              </button>
            </div>
          </div>

          <div className="pt-2 border-t border-slate-800/80 flex items-center justify-center gap-2 text-[11px] text-slate-500">
            <ShieldCheck className="w-3.5 h-3.5 text-emerald-500" />
            <span>Encrypted transmission · PBKDF2 Password Security</span>
          </div>
        </div>
      </div>
    </div>
  );
};
