import React, { useEffect, useState } from 'react';
import { api } from '../api/client';
import { Organization, OrganizationUpdatePayload, TestDbConnectionResponse, TestSmtpConnectionResponse } from '../types';
import { useToast } from '../context/ToastContext';
import { useAuth } from '../context/AuthContext';
import {
  Building,
  Key,
  Clock,
  Mail,
  MessageSquare,
  Save,
  RotateCcw,
  Sparkles,
  CheckCircle2,
  Copy,
  AlertCircle,
  Lock,
  Eye,
  EyeOff,
  ShieldCheck,
  Database,
  Server,
  Send,
  AlertTriangle,
} from 'lucide-react';

export const SettingsPage: React.FC = () => {
  const { activeOrg } = useAuth();
  const [org, setOrg] = useState<Organization | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [resettingDemo, setResettingDemo] = useState(false);
  const [copiedKey, setCopiedKey] = useState(false);

  // Password change state
  const [currentPassword, setCurrentPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [showPasswords, setShowPasswords] = useState(false);
  const [changingPassword, setChangingPassword] = useState(false);
  const [passwordError, setPasswordError] = useState<string | null>(null);

  // PostgreSQL BYODB State
  const [dbHost, setDbHost] = useState('');
  const [dbPort, setDbPort] = useState(5432);
  const [dbName, setDbName] = useState('');
  const [dbUser, setDbUser] = useState('');
  const [dbPassword, setDbPassword] = useState('');
  const [dbSslMode, setDbSslMode] = useState('prefer');
  const [showDbPassword, setShowDbPassword] = useState(false);
  const [testingDb, setTestingDb] = useState(false);
  const [savingDb, setSavingDb] = useState(false);
  const [dbTestResult, setDbTestResult] = useState<TestDbConnectionResponse | null>(null);

  // SMTP State
  const [smtpHost, setSmtpHost] = useState('');
  const [smtpPort, setSmtpPort] = useState(587);
  const [smtpUsername, setSmtpUsername] = useState('');
  const [smtpPassword, setSmtpPassword] = useState('');
  const [smtpFromAddress, setSmtpFromAddress] = useState('');
  const [smtpUseTls, setSmtpUseTls] = useState(true);
  const [smtpTestRecipient, setSmtpTestRecipient] = useState('');
  const [showSmtpPassword, setShowSmtpPassword] = useState(false);
  const [testingSmtp, setTestingSmtp] = useState(false);
  const [savingSmtp, setSavingSmtp] = useState(false);
  const [smtpTestResult, setSmtpTestResult] = useState<TestSmtpConnectionResponse | null>(null);

  // General settings state
  const [formData, setFormData] = useState<OrganizationUpdatePayload>({
    name: '',
    company_logo_url: '',
    business_timezone: 'Asia/Kolkata',
    leap_day_policy: 'feb28',
    digest_channel_id: 'general',
    slack_webhook_url: '',
    teams_webhook_url: '',
  });

  const toast = useToast();

  const fetchOrganization = async () => {
    setLoading(true);
    try {
      const data = await api.getOrganization();
      setOrg(data);
      setFormData({
        name: data.name || '',
        company_logo_url: data.company_logo_url || '',
        business_timezone: data.business_timezone || 'Asia/Kolkata',
        leap_day_policy: data.leap_day_policy || 'feb28',
        digest_channel_id: data.digest_channel_id || 'general',
        slack_webhook_url: data.slack_webhook_url || '',
        teams_webhook_url: data.teams_webhook_url || '',
      });
      // DB
      setDbHost(data.db_host || '');
      setDbPort(data.db_port || 5432);
      setDbName(data.db_name || '');
      setDbUser(data.db_user || '');
      setDbSslMode(data.db_ssl_mode || 'prefer');
      // SMTP
      setSmtpHost(data.smtp_host || '');
      setSmtpPort(data.smtp_port || 587);
      setSmtpUsername(data.smtp_username || '');
      setSmtpFromAddress(data.smtp_from_address || '');
      setSmtpUseTls(data.smtp_use_tls ?? true);
    } catch (err: any) {
      toast.error('Failed to load settings', err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchOrganization();
  }, []);

  const handleSaveGeneral = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    try {
      const updated = await api.updateOrganization(formData);
      setOrg(updated);
      toast.success('Settings Saved', 'Organization branding and general settings updated.');
    } catch (err: any) {
      toast.error('Save Failed', err.message);
    } finally {
      setSaving(false);
    }
  };

  const handleTestDatabase = async () => {
    if (!dbHost || !dbName || !dbUser || !dbPassword) {
      toast.error('Validation Error', 'Please fill in DB Host, Port, Database Name, User, and Password to test.');
      return;
    }
    setTestingDb(true);
    setDbTestResult(null);
    try {
      const res = await api.testDatabaseConnection({
        db_host: dbHost,
        db_port: Number(dbPort),
        db_name: dbName,
        db_user: dbUser,
        db_password: dbPassword,
        db_ssl_mode: dbSslMode,
      });
      setDbTestResult(res);
      if (res.success) {
        toast.success('Connection Successful', res.message);
      } else {
        toast.error('Connection Failed', res.message);
      }
    } catch (err: any) {
      const failRes: TestDbConnectionResponse = {
        success: false,
        latency_ms: null,
        server_version: null,
        message: err.message || 'Connection test failed',
      };
      setDbTestResult(failRes);
      toast.error('Connection Test Error', err.message);
    } finally {
      setTestingDb(false);
    }
  };

  const handleSaveDatabase = async () => {
    if (!dbHost || !dbName || !dbUser || !dbPassword) {
      toast.error('Validation Error', 'Please fill in DB Host, Port, Database Name, User, and Password.');
      return;
    }
    setSavingDb(true);
    try {
      const updated = await api.saveDatabaseConfiguration({
        db_host: dbHost,
        db_port: Number(dbPort),
        db_name: dbName,
        db_user: dbUser,
        db_password: dbPassword,
        db_ssl_mode: dbSslMode,
      });
      setOrg(updated);
      setDbPassword('');
      toast.success('Database Configured', 'Your private database was connected and provisioned with default templates!');
      fetchOrganization();
    } catch (err: any) {
      toast.error('Database Setup Failed', err.message);
    } finally {
      setSavingDb(false);
    }
  };

  const handleTestSmtp = async () => {
    if (!smtpHost || !smtpFromAddress) {
      toast.error('Validation Error', 'Please enter at least an SMTP Host and Sender Address.');
      return;
    }
    setTestingSmtp(true);
    setSmtpTestResult(null);
    try {
      const res = await api.testSmtpConnection({
        smtp_host: smtpHost,
        smtp_port: Number(smtpPort),
        smtp_username: smtpUsername || undefined,
        smtp_password: smtpPassword || undefined,
        smtp_from_address: smtpFromAddress,
        smtp_use_tls: smtpUseTls,
        test_recipient: smtpTestRecipient || undefined,
      });
      setSmtpTestResult(res);
      if (res.success) {
        toast.success('Email Sent', res.message);
      } else {
        toast.error('SMTP Test Failed', res.message);
      }
    } catch (err: any) {
      const failRes: TestSmtpConnectionResponse = {
        success: false,
        message: err.message || 'SMTP test failed',
      };
      setSmtpTestResult(failRes);
      toast.error('SMTP Error', err.message);
    } finally {
      setTestingSmtp(false);
    }
  };

  const handleSaveSmtp = async () => {
    if (!smtpHost || !smtpFromAddress) {
      toast.error('Validation Error', 'Please enter at least an SMTP Host and Sender Address.');
      return;
    }
    setSavingSmtp(true);
    try {
      const updated = await api.saveSmtpConfiguration({
        smtp_host: smtpHost,
        smtp_port: Number(smtpPort),
        smtp_username: smtpUsername || undefined,
        smtp_password: smtpPassword || undefined,
        smtp_from_address: smtpFromAddress,
        smtp_use_tls: smtpUseTls,
      });
      setOrg(updated);
      setSmtpPassword('');
      toast.success('SMTP Configured', 'Email provider configuration saved and verified.');
      fetchOrganization();
    } catch (err: any) {
      toast.error('SMTP Setup Failed', err.message);
    } finally {
      setSavingSmtp(false);
    }
  };

  const handleResetDemo = async () => {
    if (!confirm('This will wipe all existing logs and reload realistic sample employees. Continue?')) {
      return;
    }
    setResettingDemo(true);
    try {
      const res = await api.resetDemo();
      toast.success('Demo Reset', res.message);
      fetchOrganization();
    } catch (err: any) {
      toast.error('Reset Failed', err.message);
    } finally {
      setResettingDemo(false);
    }
  };

  const handlePasswordChange = async (e: React.FormEvent) => {
    e.preventDefault();
    setPasswordError(null);

    if (!currentPassword || !newPassword || !confirmPassword) {
      setPasswordError('All password fields are required.');
      return;
    }
    if (newPassword.length < 8) {
      setPasswordError('New password must be at least 8 characters long.');
      return;
    }
    if (newPassword !== confirmPassword) {
      setPasswordError('New password and confirmation do not match.');
      return;
    }

    setChangingPassword(true);
    try {
      await api.changePassword(currentPassword, newPassword, confirmPassword);
      toast.success('Password Updated', 'Your administrator password has been successfully updated.');
      setCurrentPassword('');
      setNewPassword('');
      setConfirmPassword('');
    } catch (err: any) {
      setPasswordError(err.message || 'Failed to update password');
      toast.error('Password Update Failed', err.message);
    } finally {
      setChangingPassword(false);
    }
  };

  const copyApiKey = () => {
    if (org?.api_key) {
      navigator.clipboard.writeText(org.api_key);
      setCopiedKey(true);
      setTimeout(() => setCopiedKey(false), 2000);
      toast.info('Copied', 'Organization API Key copied to clipboard');
    }
  };

  if (loading) {
    return (
      <div className="p-12 text-center text-slate-500 text-sm">
        <div className="w-8 h-8 border-2 border-rose-500 border-t-transparent rounded-full animate-spin mx-auto mb-3" />
        Loading organization settings...
      </div>
    );
  }

  const isSetupComplete = org?.is_setup_complete || org?.is_demo;

  return (
    <div className="max-w-4xl space-y-6">
      {/* Onboarding / Sovereignty Status Banner */}
      {isSetupComplete ? (
        <div className="p-4 rounded-2xl bg-emerald-50 border border-emerald-200 text-emerald-900 flex items-start gap-3 shadow-sm">
          <ShieldCheck className="w-5 h-5 text-emerald-600 shrink-0 mt-0.5" />
          <div className="text-xs">
            <p className="font-bold text-emerald-950">Tenant Data Sovereignty Active</p>
            <p className="text-emerald-800 mt-0.5">
              Your organization is running in dedicated isolation mode. All employee profiles, milestone records, and celebration logs are isolated to your infrastructure.
            </p>
          </div>
        </div>
      ) : (
        <div className="p-4 rounded-2xl bg-rose-50 border border-rose-200 text-rose-900 flex items-start gap-3 shadow-sm animate-pulse">
          <AlertTriangle className="w-5 h-5 text-rose-600 shrink-0 mt-0.5" />
          <div className="text-xs">
            <p className="font-bold text-rose-950">
              Setup Required: Database & Email Provider Not Yet Configured
            </p>
            <p className="text-rose-800 mt-0.5">
              <strong>You cannot add your data before you configure your database and email provider service.</strong> Please complete the PostgreSQL and SMTP configuration cards below to unlock employee creation and milestone scans.
            </p>
          </div>
        </div>
      )}

      {/* Header */}
      <div className="p-6 rounded-2xl bg-white border border-slate-100 shadow-sm flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-lg font-bold text-slate-900 flex items-center gap-2">
            <Building className="w-5 h-5 text-rose-500" />
            <span>Organization & Infrastructure Settings</span>
          </h2>
          <p className="text-xs text-slate-500 mt-1">
            Configure your private PostgreSQL database, corporate email SMTP, branding, and integrations.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={handleResetDemo}
            disabled={resettingDemo}
            className="inline-flex items-center gap-1.5 px-3.5 py-2 rounded-xl border border-amber-200 bg-amber-50 hover:bg-amber-100 text-amber-900 text-xs font-semibold transition-colors"
          >
            <RotateCcw className={`w-4 h-4 ${resettingDemo ? 'animate-spin' : ''}`} />
            <span>Reset Demo Sandbox</span>
          </button>
        </div>
      </div>

      {/* Card 1: Dedicated PostgreSQL Database (BYODB) */}
      <div className="p-6 rounded-2xl bg-white border border-slate-100 shadow-sm space-y-4">
        <div className="flex items-center justify-between border-b border-slate-100 pb-3">
          <div className="flex items-center gap-2">
            <Database className="w-5 h-5 text-blue-600" />
            <div>
              <h3 className="text-sm font-bold text-slate-800">Private PostgreSQL Database (BYODB)</h3>
              <p className="text-[11px] text-slate-400">Bring Your Own Database for complete data sovereignty & privacy</p>
            </div>
          </div>
          <div>
            {org?.is_db_configured ? (
              <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-[11px] font-semibold bg-emerald-100 text-emerald-800">
                <CheckCircle2 className="w-3.5 h-3.5" />
                Connected
              </span>
            ) : (
              <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-[11px] font-semibold bg-amber-100 text-amber-800">
                <AlertCircle className="w-3.5 h-3.5" />
                Not Configured
              </span>
            )}
          </div>
        </div>

        <p className="text-xs text-slate-500">
          All employee records, birthday & anniversary dates, templates, and delivery logs will reside in your dedicated PostgreSQL instance.
        </p>

        {dbTestResult && (
          <div
            className={`p-3 rounded-xl border text-xs flex items-start gap-2 ${
              dbTestResult.success
                ? 'bg-emerald-50 border-emerald-200 text-emerald-800'
                : 'bg-rose-50 border-rose-200 text-rose-800'
            }`}
          >
            {dbTestResult.success ? (
              <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0 mt-0.5" />
            ) : (
              <AlertCircle className="w-4 h-4 text-rose-600 shrink-0 mt-0.5" />
            )}
            <div>
              <p className="font-semibold">{dbTestResult.message}</p>
              {dbTestResult.server_version && (
                <p className="text-[11px] text-emerald-700 mt-0.5 font-mono truncate max-w-xl">
                  {dbTestResult.server_version}
                </p>
              )}
            </div>
          </div>
        )}

        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 text-xs">
          <div className="sm:col-span-2">
            <label className="block font-semibold text-slate-700 mb-1">PostgreSQL Host *</label>
            <input
              type="text"
              value={dbHost}
              onChange={(e) => setDbHost(e.target.value)}
              placeholder="e.g. postgres.internal.corp or db.mycompany.com"
              className="w-full px-3 py-2 rounded-xl border border-slate-200 focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500"
            />
          </div>

          <div>
            <label className="block font-semibold text-slate-700 mb-1">Port *</label>
            <input
              type="number"
              value={dbPort}
              onChange={(e) => setDbPort(Number(e.target.value))}
              className="w-full px-3 py-2 rounded-xl border border-slate-200 focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500"
            />
          </div>

          <div>
            <label className="block font-semibold text-slate-700 mb-1">Database Name *</label>
            <input
              type="text"
              value={dbName}
              onChange={(e) => setDbName(e.target.value)}
              placeholder="e.g. engagement_hub"
              className="w-full px-3 py-2 rounded-xl border border-slate-200 focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500"
            />
          </div>

          <div>
            <label className="block font-semibold text-slate-700 mb-1">Username *</label>
            <input
              type="text"
              value={dbUser}
              onChange={(e) => setDbUser(e.target.value)}
              placeholder="e.g. postgres or app_user"
              className="w-full px-3 py-2 rounded-xl border border-slate-200 focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500"
            />
          </div>

          <div>
            <div className="flex items-center justify-between mb-1">
              <label className="font-semibold text-slate-700">Password *</label>
              <button
                type="button"
                onClick={() => setShowDbPassword(!showDbPassword)}
                className="text-[11px] text-slate-400 hover:text-slate-600"
              >
                {showDbPassword ? 'Hide' : 'Show'}
              </button>
            </div>
            <input
              type={showDbPassword ? 'text' : 'password'}
              value={dbPassword}
              onChange={(e) => setDbPassword(e.target.value)}
              placeholder="••••••••••••"
              className="w-full px-3 py-2 rounded-xl border border-slate-200 focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500"
            />
          </div>

          <div>
            <label className="block font-semibold text-slate-700 mb-1">SSL Mode</label>
            <select
              value={dbSslMode}
              onChange={(e) => setDbSslMode(e.target.value)}
              className="w-full px-3 py-2 rounded-xl border border-slate-200 focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500"
            >
              <option value="prefer">prefer (Default)</option>
              <option value="require">require</option>
              <option value="disable">disable</option>
              <option value="verify-ca">verify-ca</option>
              <option value="verify-full">verify-full</option>
            </select>
          </div>
        </div>

        <div className="flex items-center gap-3 pt-2">
          <button
            type="button"
            onClick={handleTestDatabase}
            disabled={testingDb}
            className="inline-flex items-center gap-1.5 px-4 py-2 rounded-xl border border-slate-200 hover:bg-slate-50 text-slate-700 text-xs font-semibold transition-colors cursor-pointer"
          >
            <Server className={`w-4 h-4 ${testingDb ? 'animate-spin' : ''}`} />
            <span>{testingDb ? 'Testing Connection...' : 'Test Connection'}</span>
          </button>

          <button
            type="button"
            onClick={handleSaveDatabase}
            disabled={savingDb}
            className="inline-flex items-center gap-1.5 px-4 py-2 rounded-xl bg-blue-600 hover:bg-blue-700 text-white text-xs font-semibold shadow-sm transition-colors cursor-pointer"
          >
            <Save className={`w-4 h-4 ${savingDb ? 'animate-spin' : ''}`} />
            <span>{savingDb ? 'Provisioning Schema...' : 'Save & Provision Database'}</span>
          </button>
        </div>
      </div>

      {/* Card 2: Dedicated Email Provider (SMTP) */}
      <div className="p-6 rounded-2xl bg-white border border-slate-100 shadow-sm space-y-4">
        <div className="flex items-center justify-between border-b border-slate-100 pb-3">
          <div className="flex items-center gap-2">
            <Mail className="w-5 h-5 text-indigo-600" />
            <div>
              <h3 className="text-sm font-bold text-slate-800">Email Delivery Provider (SMTP)</h3>
              <p className="text-[11px] text-slate-400">Configure corporate SMTP or transactional relay for celebrations</p>
            </div>
          </div>
          <div>
            {org?.is_smtp_configured ? (
              <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-[11px] font-semibold bg-emerald-100 text-emerald-800">
                <CheckCircle2 className="w-3.5 h-3.5" />
                Configured
              </span>
            ) : (
              <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-[11px] font-semibold bg-amber-100 text-amber-800">
                <AlertCircle className="w-3.5 h-3.5" />
                Not Configured
              </span>
            )}
          </div>
        </div>

        <p className="text-xs text-slate-500">
          Send individual celebratory messages and daily team digest announcements from your own verified company domain.
        </p>

        {smtpTestResult && (
          <div
            className={`p-3 rounded-xl border text-xs flex items-start gap-2 ${
              smtpTestResult.success
                ? 'bg-emerald-50 border-emerald-200 text-emerald-800'
                : 'bg-rose-50 border-rose-200 text-rose-800'
            }`}
          >
            {smtpTestResult.success ? (
              <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0 mt-0.5" />
            ) : (
              <AlertCircle className="w-4 h-4 text-rose-600 shrink-0 mt-0.5" />
            )}
            <p className="font-semibold">{smtpTestResult.message}</p>
          </div>
        )}

        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 text-xs">
          <div className="sm:col-span-2">
            <label className="block font-semibold text-slate-700 mb-1">SMTP Host *</label>
            <input
              type="text"
              value={smtpHost}
              onChange={(e) => setSmtpHost(e.target.value)}
              placeholder="e.g. smtp.sendgrid.net or smtp.gmail.com"
              className="w-full px-3 py-2 rounded-xl border border-slate-200 focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500"
            />
          </div>

          <div>
            <label className="block font-semibold text-slate-700 mb-1">Port *</label>
            <input
              type="number"
              value={smtpPort}
              onChange={(e) => setSmtpPort(Number(e.target.value))}
              className="w-full px-3 py-2 rounded-xl border border-slate-200 focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500"
            />
          </div>

          <div>
            <label className="block font-semibold text-slate-700 mb-1">Username / API Key</label>
            <input
              type="text"
              value={smtpUsername}
              onChange={(e) => setSmtpUsername(e.target.value)}
              placeholder="e.g. apikey or notifications@corp.com"
              className="w-full px-3 py-2 rounded-xl border border-slate-200 focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500"
            />
          </div>

          <div>
            <div className="flex items-center justify-between mb-1">
              <label className="font-semibold text-slate-700">Password / Secret</label>
              <button
                type="button"
                onClick={() => setShowSmtpPassword(!showSmtpPassword)}
                className="text-[11px] text-slate-400 hover:text-slate-600"
              >
                {showSmtpPassword ? 'Hide' : 'Show'}
              </button>
            </div>
            <input
              type={showSmtpPassword ? 'text' : 'password'}
              value={smtpPassword}
              onChange={(e) => setSmtpPassword(e.target.value)}
              placeholder="••••••••••••"
              className="w-full px-3 py-2 rounded-xl border border-slate-200 focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500"
            />
          </div>

          <div>
            <label className="block font-semibold text-slate-700 mb-1">From Email Address *</label>
            <input
              type="email"
              value={smtpFromAddress}
              onChange={(e) => setSmtpFromAddress(e.target.value)}
              placeholder="celebrations@yourcompany.com"
              className="w-full px-3 py-2 rounded-xl border border-slate-200 focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500"
            />
          </div>

          <div className="sm:col-span-2 flex items-center gap-2 pt-2">
            <input
              type="checkbox"
              id="smtpUseTls"
              checked={smtpUseTls}
              onChange={(e) => setSmtpUseTls(e.target.checked)}
              className="rounded text-indigo-600 focus:ring-indigo-500 h-4 w-4"
            />
            <label htmlFor="smtpUseTls" className="font-semibold text-slate-700 cursor-pointer">
              Enable STARTTLS encryption (Recommended for port 587)
            </label>
          </div>

          <div className="sm:col-span-3">
            <label className="block font-semibold text-slate-700 mb-1">Test Recipient Email (Optional)</label>
            <input
              type="email"
              value={smtpTestRecipient}
              onChange={(e) => setSmtpTestRecipient(e.target.value)}
              placeholder="Defaults to your administrator email"
              className="w-full sm:w-1/2 px-3 py-2 rounded-xl border border-slate-200 focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500"
            />
          </div>
        </div>

        <div className="flex items-center gap-3 pt-2">
          <button
            type="button"
            onClick={handleTestSmtp}
            disabled={testingSmtp}
            className="inline-flex items-center gap-1.5 px-4 py-2 rounded-xl border border-slate-200 hover:bg-slate-50 text-slate-700 text-xs font-semibold transition-colors cursor-pointer"
          >
            <Send className={`w-4 h-4 ${testingSmtp ? 'animate-spin' : ''}`} />
            <span>{testingSmtp ? 'Sending Test...' : 'Send Live Test Email'}</span>
          </button>

          <button
            type="button"
            onClick={handleSaveSmtp}
            disabled={savingSmtp}
            className="inline-flex items-center gap-1.5 px-4 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-semibold shadow-sm transition-colors cursor-pointer"
          >
            <Save className={`w-4 h-4 ${savingSmtp ? 'animate-spin' : ''}`} />
            <span>{savingSmtp ? 'Saving SMTP...' : 'Save SMTP Settings'}</span>
          </button>
        </div>
      </div>

      <form onSubmit={handleSaveGeneral} className="space-y-6">
        {/* Section 3: Company Profile */}
        <div className="p-6 rounded-2xl bg-white border border-slate-100 shadow-sm space-y-4">
          <h3 className="text-sm font-bold text-slate-800 flex items-center gap-2 border-b border-slate-100 pb-3">
            <Sparkles className="w-4 h-4 text-rose-500" />
            <span>Company Branding</span>
          </h3>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-xs">
            <div>
              <label className="block font-semibold text-slate-700 mb-1">Company / Organization Name *</label>
              <input
                type="text"
                required
                value={formData.name || ''}
                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                className="w-full px-3 py-2 rounded-xl border border-slate-200 focus:outline-none focus:ring-2 focus:ring-rose-500/20 focus:border-rose-500"
                placeholder="e.g. Acme Corporation"
              />
            </div>

            <div>
              <label className="block font-semibold text-slate-700 mb-1">Company Logo URL</label>
              <input
                type="url"
                value={formData.company_logo_url || ''}
                onChange={(e) => setFormData({ ...formData, company_logo_url: e.target.value })}
                className="w-full px-3 py-2 rounded-xl border border-slate-200 focus:outline-none focus:ring-2 focus:ring-rose-500/20 focus:border-rose-500"
                placeholder="https://assets.yourcompany.com/logo.png"
              />
            </div>
          </div>
        </div>

        {/* Section 4: Timezone & Leap Year Policy */}
        <div className="p-6 rounded-2xl bg-white border border-slate-100 shadow-sm space-y-4">
          <h3 className="text-sm font-bold text-slate-800 flex items-center gap-2 border-b border-slate-100 pb-3">
            <Clock className="w-4 h-4 text-sky-500" />
            <span>Scheduling & Timezone</span>
          </h3>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-xs">
            <div>
              <label className="block font-semibold text-slate-700 mb-1">Business Timezone *</label>
              <select
                value={formData.business_timezone || 'Asia/Kolkata'}
                onChange={(e) => setFormData({ ...formData, business_timezone: e.target.value })}
                className="w-full px-3 py-2 rounded-xl border border-slate-200 focus:outline-none focus:ring-2 focus:ring-rose-500/20 focus:border-rose-500 cursor-pointer"
              >
                <option value="Asia/Kolkata">Asia/Kolkata (IST +5:30)</option>
                <option value="America/New_York">America/New_York (EST/EDT -5:00)</option>
                <option value="America/Los_Angeles">America/Los_Angeles (PST/PDT -8:00)</option>
                <option value="America/Chicago">America/Chicago (CST/CDT -6:00)</option>
                <option value="Europe/London">Europe/London (GMT/BST +0:00)</option>
                <option value="Europe/Paris">Europe/Paris (CET/CEST +1:00)</option>
                <option value="Asia/Singapore">Asia/Singapore (SGT +8:00)</option>
                <option value="Asia/Dubai">Asia/Dubai (GST +4:00)</option>
                <option value="Australia/Sydney">Australia/Sydney (AEST/AEDT +10:00)</option>
              </select>
              <p className="text-[11px] text-slate-400 mt-1">
                Daily milestone scans run at 08:00 AM in this organization's timezone.
              </p>
            </div>

            <div>
              <label className="block font-semibold text-slate-700 mb-1">Feb 29 Leap-Year Policy</label>
              <select
                value={formData.leap_day_policy || 'feb28'}
                onChange={(e) => setFormData({ ...formData, leap_day_policy: e.target.value })}
                className="w-full px-3 py-2 rounded-xl border border-slate-200 focus:outline-none focus:ring-2 focus:ring-rose-500/20 focus:border-rose-500 cursor-pointer"
              >
                <option value="feb28">Celebrate on Feb 28 in non-leap years (Recommended)</option>
                <option value="mar1">Celebrate on Mar 1 in non-leap years</option>
                <option value="leap_only">Only celebrate in actual leap years</option>
              </select>
            </div>
          </div>
        </div>

        {/* Section 5: Webhooks & Delivery Channels */}
        <div className="p-6 rounded-2xl bg-white border border-slate-100 shadow-sm space-y-4">
          <h3 className="text-sm font-bold text-slate-800 flex items-center gap-2 border-b border-slate-100 pb-3">
            <MessageSquare className="w-4 h-4 text-emerald-500" />
            <span>Slack & MS Teams Channels</span>
          </h3>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-xs">
            <div>
              <label className="block font-semibold text-slate-700 mb-1">Slack Incoming Webhook URL</label>
              <input
                type="url"
                value={formData.slack_webhook_url || ''}
                onChange={(e) => setFormData({ ...formData, slack_webhook_url: e.target.value })}
                className="w-full px-3 py-2 rounded-xl border border-slate-200 focus:outline-none focus:ring-2 focus:ring-rose-500/20 focus:border-rose-500"
                placeholder="https://hooks.slack.com/services/..."
              />
            </div>

            <div>
              <label className="block font-semibold text-slate-700 mb-1">Default Digest Channel Name / ID</label>
              <input
                type="text"
                value={formData.digest_channel_id || ''}
                onChange={(e) => setFormData({ ...formData, digest_channel_id: e.target.value })}
                className="w-full px-3 py-2 rounded-xl border border-slate-200 focus:outline-none focus:ring-2 focus:ring-rose-500/20 focus:border-rose-500"
                placeholder="e.g. general or #celebrations"
              />
            </div>
          </div>
        </div>

        {/* Save Button for General Branding */}
        <div className="flex justify-end">
          <button
            type="submit"
            disabled={saving}
            className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl bg-rose-600 hover:bg-rose-700 text-white text-xs font-semibold shadow-md shadow-rose-900/20 transition-all cursor-pointer"
          >
            <Save className={`w-4 h-4 ${saving ? 'animate-spin' : ''}`} />
            <span>{saving ? 'Saving...' : 'Save General Settings'}</span>
          </button>
        </div>
      </form>

      {/* Section 6: API Access */}
      <div className="p-6 rounded-2xl bg-white border border-slate-100 shadow-sm space-y-4">
        <h3 className="text-sm font-bold text-slate-800 flex items-center gap-2 border-b border-slate-100 pb-3">
          <Key className="w-4 h-4 text-indigo-500" />
          <span>Organization API Credentials</span>
        </h3>

        <div className="text-xs space-y-2">
          <label className="block font-semibold text-slate-700">Organization API Key (x-api-key)</label>
          <div className="flex items-center gap-2">
            <input
              type="password"
              readOnly
              value={org?.api_key || ''}
              className="flex-1 font-mono px-3 py-2 bg-slate-50 rounded-xl border border-slate-200 text-slate-600"
            />
            <button
              type="button"
              onClick={copyApiKey}
              className="inline-flex items-center gap-1.5 px-3 py-2 rounded-xl border border-slate-200 hover:bg-slate-100 text-slate-700 font-semibold transition-colors cursor-pointer"
            >
              {copiedKey ? <CheckCircle2 className="w-4 h-4 text-emerald-600" /> : <Copy className="w-4 h-4" />}
              <span>{copiedKey ? 'Copied' : 'Copy Key'}</span>
            </button>
          </div>
          <p className="text-[11px] text-slate-400">
            Use this key in the <code className="bg-slate-100 px-1 py-0.5 rounded text-slate-700">x-api-key</code> header to trigger scans and manage employees programmatically.
          </p>
        </div>
      </div>

      {/* Section 7: Security & Administrator Password */}
      <div className="p-6 rounded-2xl bg-white border border-slate-100 shadow-sm space-y-4">
        <div className="flex items-center justify-between border-b border-slate-100 pb-3">
          <h3 className="text-sm font-bold text-slate-800 flex items-center gap-2">
            <Lock className="w-4 h-4 text-rose-500" />
            <span>Administrator Password & Security</span>
          </h3>
          <button
            type="button"
            onClick={() => setShowPasswords(!showPasswords)}
            className="inline-flex items-center gap-1.5 text-xs font-semibold text-slate-500 hover:text-slate-800 transition-colors cursor-pointer"
          >
            {showPasswords ? <EyeOff className="w-3.5 h-3.5" /> : <Eye className="w-3.5 h-3.5" />}
            <span>{showPasswords ? 'Hide Passwords' : 'Show Passwords'}</span>
          </button>
        </div>

        <p className="text-xs text-slate-500">
          Rotate your organization admin credentials. Passwords must be at least 8 characters long.
        </p>

        {passwordError && (
          <div className="flex items-center gap-2 p-3 rounded-xl bg-rose-50 border border-rose-200 text-rose-800 text-xs">
            <AlertCircle className="w-4 h-4 text-rose-600 shrink-0" />
            <span>{passwordError}</span>
          </div>
        )}

        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 text-xs">
          <div>
            <label className="block font-semibold text-slate-700 mb-1">Current Password</label>
            <input
              type={showPasswords ? 'text' : 'password'}
              value={currentPassword}
              onChange={(e) => {
                setPasswordError(null);
                setCurrentPassword(e.target.value);
              }}
              className="w-full px-3 py-2 rounded-xl border border-slate-200 focus:outline-none focus:ring-2 focus:ring-rose-500/20 focus:border-rose-500"
              placeholder="••••••••"
            />
          </div>

          <div>
            <label className="block font-semibold text-slate-700 mb-1">New Password</label>
            <input
              type={showPasswords ? 'text' : 'password'}
              value={newPassword}
              onChange={(e) => {
                setPasswordError(null);
                setNewPassword(e.target.value);
              }}
              className="w-full px-3 py-2 rounded-xl border border-slate-200 focus:outline-none focus:ring-2 focus:ring-rose-500/20 focus:border-rose-500"
              placeholder="••••••••"
            />
          </div>

          <div>
            <label className="block font-semibold text-slate-700 mb-1">Confirm New Password</label>
            <input
              type={showPasswords ? 'text' : 'password'}
              value={confirmPassword}
              onChange={(e) => {
                setPasswordError(null);
                setConfirmPassword(e.target.value);
              }}
              className="w-full px-3 py-2 rounded-xl border border-slate-200 focus:outline-none focus:ring-2 focus:ring-rose-500/20 focus:border-rose-500"
              placeholder="••••••••"
            />
          </div>
        </div>

        <div className="flex justify-end pt-2">
          <button
            type="button"
            onClick={handlePasswordChange}
            disabled={changingPassword}
            className="inline-flex items-center gap-1.5 px-4 py-2 rounded-xl border border-slate-200 hover:bg-slate-50 text-slate-700 text-xs font-semibold transition-colors cursor-pointer"
          >
            <ShieldCheck className={`w-4 h-4 ${changingPassword ? 'animate-spin' : ''}`} />
            <span>{changingPassword ? 'Updating...' : 'Update Admin Password'}</span>
          </button>
        </div>
      </div>
    </div>
  );
};
