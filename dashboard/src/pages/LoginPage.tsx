import React, { useState } from 'react';
import { useAuth } from '../context/AuthContext';
import { Sparkles, Key, AlertCircle, ArrowRight, ShieldCheck } from 'lucide-react';

export const LoginPage: React.FC = () => {
  const { login, authError, clearAuthError } = useAuth();
  const [apiKeyInput, setApiKeyInput] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!apiKeyInput.trim()) return;

    setIsSubmitting(true);
    await login(apiKeyInput);
    setIsSubmitting(false);
  };

  return (
    <div className="min-h-screen bg-slate-900 flex flex-col justify-center items-center px-4 sm:px-6 lg:px-8 relative overflow-hidden">
      {/* Background Glows */}
      <div className="absolute top-1/4 -left-20 w-96 h-96 bg-rose-500/10 rounded-full blur-3xl pointer-events-none" />
      <div className="absolute bottom-1/4 -right-20 w-96 h-96 bg-purple-500/10 rounded-full blur-3xl pointer-events-none" />

      <div className="max-w-md w-full space-y-8 relative z-10">
        {/* Header Branding */}
        <div className="text-center space-y-2">
          <div className="inline-flex items-center justify-center w-14 h-14 rounded-2xl bg-gradient-to-tr from-rose-500 to-pink-500 text-white shadow-xl shadow-rose-500/20 mb-2">
            <Sparkles className="w-7 h-7" />
          </div>
          <h2 className="text-2xl sm:text-3xl font-extrabold text-white tracking-tight">
            Team Engagement Service
          </h2>
          <p className="text-sm text-slate-400">
            Operations & Management Console
          </p>
        </div>

        {/* Login Card */}
        <div className="bg-slate-800/80 border border-slate-700/80 rounded-2xl p-6 sm:p-8 shadow-2xl backdrop-blur-xl space-y-6">
          <div className="space-y-1">
            <h3 className="text-base font-semibold text-white">Admin Authentication</h3>
            <p className="text-xs text-slate-400 leading-relaxed">
              Enter the admin API key configured for this service. Key is kept in session memory only for this tab.
            </p>
          </div>

          {authError && (
            <div className="flex items-start gap-3 p-3.5 rounded-xl bg-rose-500/10 border border-rose-500/30 text-rose-300 text-xs">
              <AlertCircle className="w-4 h-4 text-rose-400 shrink-0 mt-0.5" />
              <div className="flex-1 min-w-0">
                <span className="font-semibold block">Authentication Error</span>
                <span className="opacity-90">{authError}</span>
              </div>
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label
                htmlFor="apiKey"
                className="block text-xs font-semibold uppercase tracking-wider text-slate-300 mb-1.5"
              >
                Admin API Key (<code className="text-rose-400 lowercase">x-api-key</code>)
              </label>
              <div className="relative">
                <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-slate-500">
                  <Key className="w-4 h-4" />
                </div>
                <input
                  id="apiKey"
                  type="password"
                  value={apiKeyInput}
                  onChange={(e) => {
                    if (authError) clearAuthError();
                    setApiKeyInput(e.target.value);
                  }}
                  placeholder="Enter ADMIN_API_KEY..."
                  required
                  autoFocus
                  className="w-full pl-10 pr-4 py-2.5 rounded-xl border border-slate-600 bg-slate-900/80 text-white placeholder-slate-500 text-sm focus:outline-none focus:ring-2 focus:ring-rose-500 focus:border-rose-500 transition-all font-mono"
                />
              </div>
            </div>

            <button
              type="submit"
              disabled={isSubmitting || !apiKeyInput.trim()}
              className="w-full flex items-center justify-center gap-2 py-2.5 px-4 rounded-xl text-sm font-semibold text-white bg-rose-600 hover:bg-rose-500 disabled:opacity-50 disabled:cursor-not-allowed transition-all shadow-lg shadow-rose-600/20 active:scale-98"
            >
              {isSubmitting ? (
                <>
                  <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                  <span>Validating Key...</span>
                </>
              ) : (
                <>
                  <span>Sign In to Console</span>
                  <ArrowRight className="w-4 h-4" />
                </>
              )}
            </button>
          </form>

          <div className="pt-4 border-t border-slate-700/60 flex items-center justify-center gap-2 text-xs text-slate-500">
            <ShieldCheck className="w-4 h-4 text-emerald-500" />
            <span>Encrypted transmission · Zero persistent disk storage</span>
          </div>
        </div>
      </div>
    </div>
  );
};
