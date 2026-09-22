import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { EngagementMotionGraphic } from '../components/auth/EngagementMotionGraphic';
import {
  Sparkles,
  Mail,
  Lock,
  ArrowRight,
  ShieldCheck,
  Eye,
  EyeOff,
  AlertCircle,
  HelpCircle,
  X,
  Loader2,
} from 'lucide-react';

export const LoginPage: React.FC = () => {
  const navigate = useNavigate();
  const { loginWithEmail, isSuperAdmin, authError, clearAuthError } = useAuth();

  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [rememberEmail, setRememberEmail] = useState(false);
  const [showForgotHelp, setShowForgotHelp] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);

  // Restore remembered email on mount
  useEffect(() => {
    const savedEmail = localStorage.getItem('remembered_email');
    if (savedEmail) {
      setEmail(savedEmail);
      setRememberEmail(true);
    }
  }, []);

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    const cleanEmail = email.trim();
    if (!cleanEmail || !password.trim() || isSubmitting) return;

    setIsSubmitting(true);
    const success = await loginWithEmail(cleanEmail, password);
    setIsSubmitting(false);

    if (success) {
      if (rememberEmail) {
        localStorage.setItem('remembered_email', cleanEmail);
      } else {
        localStorage.removeItem('remembered_email');
      }
      navigate(isSuperAdmin ? '/superadmin/organizations' : '/overview', { replace: true });
    }
  };

  const handleEmailChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (authError) clearAuthError();
    setEmail(e.target.value);
  };

  const handlePasswordChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (authError) clearAuthError();
    setPassword(e.target.value);
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex items-center justify-center p-4 sm:p-6 lg:p-8 relative overflow-hidden select-none">
      {/* Subtle Starry Dot Matrix Grid */}
      <div className="fixed inset-0 bg-[radial-gradient(#ffffff0d_1px,transparent_1px)] [background-size:24px_24px] pointer-events-none z-0" />

      {/* Luminous Ambient Background Glows */}
      <div className="fixed top-1/4 left-1/4 w-[42rem] h-[42rem] bg-rose-600/10 rounded-full blur-[140px] pointer-events-none animate-pulse-glow z-0" />
      <div className="fixed bottom-1/4 right-1/4 w-[42rem] h-[42rem] bg-indigo-600/10 rounded-full blur-[140px] pointer-events-none animate-pulse-glow z-0" style={{ animationDelay: '3s' }} />

      {/* Interactive Full-Screen Constellation & Milestone Canvas */}
      <EngagementMotionGraphic />

      {/* Production-Ready Centered Sign-In Card */}
      <div className="w-full max-w-md sm:max-w-lg relative z-10 mx-auto">
        {/* Brand Header */}
        <div className="text-center mb-6">
          <div className="inline-flex items-center justify-center p-3.5 bg-gradient-to-tr from-rose-500/20 via-pink-500/15 to-indigo-500/20 border border-rose-500/35 rounded-2xl shadow-xl shadow-rose-950/50 mb-3 ring-1 ring-white/10">
            <Sparkles className="w-8 h-8 text-rose-400" />
          </div>
          <h1 className="text-2xl sm:text-3xl font-extrabold text-white tracking-tight">
            Team Engagement Portal
          </h1>
          <p className="text-xs sm:text-sm text-slate-400 mt-1">
            Sign in with your organization credentials
          </p>
        </div>

        {/* Sign In Glassmorphic Card */}
        <div className="bg-slate-900/80 backdrop-blur-2xl border border-slate-800/90 rounded-3xl shadow-2xl p-7 sm:p-10 relative overflow-hidden">
          {/* Subtle Top Card Sheen */}
          <div className="absolute top-0 left-0 right-0 h-[2px] bg-gradient-to-r from-transparent via-rose-500/60 to-transparent" />

          {/* Error Alert */}
          {authError && (
            <div className="mb-5 p-3.5 rounded-xl bg-rose-500/10 border border-rose-500/30 text-rose-300 text-xs flex items-start justify-between gap-3 animate-in fade-in duration-200">
              <div className="flex items-start gap-2.5">
                <AlertCircle className="w-4 h-4 flex-shrink-0 mt-0.5 text-rose-400" />
                <span className="leading-relaxed">{authError}</span>
              </div>
              <button
                type="button"
                onClick={clearAuthError}
                className="text-rose-400 hover:text-rose-200 transition-colors p-0.5 rounded"
                title="Dismiss"
              >
                <X className="w-3.5 h-3.5" />
              </button>
            </div>
          )}

          {/* Login Form */}
          <form onSubmit={handleLogin} className="space-y-4 sm:space-y-5">
            <div>
              <label
                htmlFor="login-email"
                className="block text-xs font-semibold uppercase tracking-wider text-slate-300 mb-2"
              >
                Work Email Address
              </label>
              <div className="relative">
                <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-slate-500">
                  <Mail className="w-4 h-4" />
                </div>
                <input
                  id="login-email"
                  type="email"
                  required
                  autoComplete="email"
                  value={email}
                  onChange={handleEmailChange}
                  placeholder="name@company.com"
                  className="w-full pl-10 pr-4 py-2.5 sm:py-3 bg-slate-950/70 border border-slate-700/70 rounded-xl text-slate-100 placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-rose-500/40 focus:border-rose-500 text-sm transition-all shadow-inner"
                />
              </div>
            </div>

            <div>
              <div className="flex items-center justify-between mb-2">
                <label
                  htmlFor="login-password"
                  className="block text-xs font-semibold uppercase tracking-wider text-slate-300"
                >
                  Password
                </label>
                <button
                  type="button"
                  onClick={() => setShowForgotHelp(true)}
                  className="text-xs text-rose-400 hover:text-rose-300 font-medium transition-colors"
                >
                  Forgot password?
                </button>
              </div>
              <div className="relative">
                <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-slate-500">
                  <Lock className="w-4 h-4" />
                </div>
                <input
                  id="login-password"
                  type={showPassword ? 'text' : 'password'}
                  required
                  autoComplete="current-password"
                  value={password}
                  onChange={handlePasswordChange}
                  placeholder="••••••••"
                  className="w-full pl-10 pr-11 py-2.5 sm:py-3 bg-slate-950/70 border border-slate-700/70 rounded-xl text-slate-100 placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-rose-500/40 focus:border-rose-500 text-sm transition-all shadow-inner"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute inset-y-0 right-0 pr-3.5 flex items-center text-slate-400 hover:text-slate-200 transition-colors"
                  aria-label={showPassword ? 'Hide password' : 'Show password'}
                >
                  {showPassword ? (
                    <EyeOff className="w-4 h-4" />
                  ) : (
                    <Eye className="w-4 h-4" />
                  )}
                </button>
              </div>
            </div>

            <div className="flex items-center justify-between pt-1">
              <label className="flex items-center gap-2 cursor-pointer select-none">
                <input
                  type="checkbox"
                  checked={rememberEmail}
                  onChange={(e) => setRememberEmail(e.target.checked)}
                  className="w-4 h-4 rounded border-slate-700 bg-slate-950 text-rose-500 focus:ring-rose-500/30 focus:ring-offset-0 transition-colors cursor-pointer"
                />
                <span className="text-xs text-slate-400">Remember email on this device</span>
              </label>
            </div>

            <button
              type="submit"
              disabled={isSubmitting || !email.trim() || !password.trim()}
              className="w-full mt-2 py-3 sm:py-3.5 px-4 bg-gradient-to-r from-rose-500 via-pink-500 to-rose-600 hover:from-rose-600 hover:via-pink-600 hover:to-rose-700 disabled:opacity-50 disabled:cursor-not-allowed text-white font-semibold text-sm rounded-xl shadow-lg shadow-rose-950/60 flex items-center justify-center gap-2 transition-all transform active:scale-[0.99] group cursor-pointer"
            >
              {isSubmitting ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  <span>Authenticating...</span>
                </>
              ) : (
                <>
                  <span>Sign In to Portal</span>
                  <ArrowRight className="w-4 h-4 group-hover:translate-x-1 transition-transform" />
                </>
              )}
            </button>
          </form>

          {/* Security Assurance Badge */}
          <div className="mt-8 pt-5 border-t border-slate-800/80 flex items-center justify-center gap-2 text-slate-400 text-xs">
            <ShieldCheck className="w-4 h-4 text-emerald-400 flex-shrink-0" />
            <span>Encrypted Session • Role-Based Access Control</span>
          </div>
        </div>
      </div>

      {/* Support Help Modal */}
      {showForgotHelp && (
        <div className="fixed inset-0 bg-slate-950/80 backdrop-blur-sm flex items-center justify-center z-50 p-4 animate-in fade-in duration-150">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl max-w-sm w-full p-6 shadow-2xl relative">
            <button
              onClick={() => setShowForgotHelp(false)}
              className="absolute top-4 right-4 text-slate-400 hover:text-slate-200"
            >
              <X className="w-5 h-5" />
            </button>
            <div className="flex items-center gap-3 mb-3">
              <div className="p-2 bg-indigo-500/10 text-indigo-400 rounded-lg">
                <HelpCircle className="w-5 h-5" />
              </div>
              <h3 className="text-base font-semibold text-white">
                Reset Password Help
              </h3>
            </div>
            <p className="text-sm text-slate-300 mb-4 leading-relaxed">
              To update or reset your password, please contact your organization administrator.
              If you are an organization administrator, contact the platform super administrator to reset your credentials.
            </p>
            <button
              onClick={() => setShowForgotHelp(false)}
              className="w-full py-2 bg-slate-800 hover:bg-slate-700 text-white rounded-xl text-xs font-semibold transition-colors"
            >
              Understood
            </button>
          </div>
        </div>
      )}
    </div>
  );
};
