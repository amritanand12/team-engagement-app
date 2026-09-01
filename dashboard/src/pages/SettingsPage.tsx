import React, { useEffect, useState } from 'react';
import { api } from '../api/client';
import { Organization, OrganizationUpdatePayload } from '../types';
import { useToast } from '../context/ToastContext';
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
} from 'lucide-react';

export const SettingsPage: React.FC = () => {
  const [org, setOrg] = useState<Organization | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [resettingDemo, setResettingDemo] = useState(false);
  const [copiedKey, setCopiedKey] = useState(false);

  const [formData, setFormData] = useState<OrganizationUpdatePayload>({
    name: '',
    company_logo_url: '',
    business_timezone: 'Asia/Kolkata',
    leap_day_policy: 'feb28',
    digest_channel_id: 'general',
    smtp_host: '',
    smtp_port: 587,
    smtp_username: '',
    smtp_password: '',
    smtp_from_address: '',
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
        smtp_host: data.smtp_host || '',
        smtp_port: data.smtp_port || 587,
        smtp_username: data.smtp_username || '',
        smtp_from_address: data.smtp_from_address || '',
        slack_webhook_url: data.slack_webhook_url || '',
        teams_webhook_url: data.teams_webhook_url || '',
      });
    } catch (err: any) {
      toast.error('Failed to load settings', err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchOrganization();
  }, []);

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    try {
      const updated = await api.updateOrganization(formData);
      setOrg(updated);
      toast.success('Settings Saved', 'Organization profile and delivery settings updated.');
    } catch (err: any) {
      toast.error('Save Failed', err.message);
    } finally {
      setSaving(false);
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

  return (
    <div className="max-w-4xl space-y-6">
      {/* Header */}
      <div className="p-6 rounded-2xl bg-white border border-slate-100 shadow-sm flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-lg font-bold text-slate-900 flex items-center gap-2">
            <Building className="w-5 h-5 text-rose-500" />
            <span>Organization & Delivery Settings</span>
          </h2>
          <p className="text-xs text-slate-500 mt-1">
            Configure company branding, local timezones, notifications, and integration channels.
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

      <form onSubmit={handleSave} className="space-y-6">
        {/* Section 1: Company Profile */}
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

        {/* Section 2: Timezone & Leap Year Policy */}
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

        {/* Section 3: Webhooks & Delivery Channels */}
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

        {/* Section 4: API Access */}
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
                className="inline-flex items-center gap-1.5 px-3 py-2 rounded-xl border border-slate-200 hover:bg-slate-100 text-slate-700 font-semibold transition-colors"
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

        {/* Action Button */}
        <div className="flex justify-end pt-2">
          <button
            type="submit"
            disabled={saving}
            className="inline-flex items-center gap-2 px-6 py-2.5 rounded-xl bg-rose-600 hover:bg-rose-700 text-white font-semibold text-xs shadow-md transition-colors disabled:opacity-50"
          >
            <Save className="w-4 h-4" />
            <span>{saving ? 'Saving Changes...' : 'Save Settings'}</span>
          </button>
        </div>
      </form>
    </div>
  );
};
