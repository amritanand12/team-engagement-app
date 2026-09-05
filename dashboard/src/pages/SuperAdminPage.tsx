import React, { useEffect, useState } from 'react';
import { api } from '../api/client';
import { CreateTenantPayload, SuperAdminOrg } from '../types';
import { useAuth } from '../context/AuthContext';
import { useToast } from '../context/ToastContext';
import { Modal } from '../components/common/Modal';
import {
  Crown,
  Building,
  Plus,
  Users,
  CalendarCheck,
  Power,
  ExternalLink,
  Copy,
  CheckCircle2,
  RefreshCw,
  Clock,
  Sparkles,
  Lock,
  Key,
  Trash2,
} from 'lucide-react';

interface SuperAdminPageProps {
  onSwitchToTenant: () => void;
}

export const SuperAdminPage: React.FC<SuperAdminPageProps> = ({ onSwitchToTenant }) => {
  const { switchTenant } = useAuth();
  const toast = useToast();

  const [orgs, setOrgs] = useState<SuperAdminOrg[]>([]);
  const [loading, setLoading] = useState(true);
  const [copiedKeyId, setCopiedKeyId] = useState<string | null>(null);

  // Reset Password Modal
  const [isResetModalOpen, setIsResetModalOpen] = useState(false);
  const [resettingOrg, setResettingOrg] = useState<SuperAdminOrg | null>(null);
  const [newTenantPassword, setNewTenantPassword] = useState('');
  const [resettingPassword, setResettingPassword] = useState(false);

  // Create Tenant Modal
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [formData, setFormData] = useState<CreateTenantPayload>({
    name: '',
    slug: '',
    admin_email: '',
    admin_name: '',
    admin_password: '',
    business_timezone: 'Asia/Kolkata',
    leap_day_policy: 'feb28',
  });

  const fetchOrganizations = async () => {
    setLoading(true);
    try {
      const data = await api.getSuperAdminOrganizations();
      setOrgs(data);
    } catch (err: any) {
      toast.error('Failed to load organizations', err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchOrganizations();
  }, []);

  const handleCreateTenant = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    try {
      const newOrg = await api.createOrganization(formData);
      toast.success(
        'Tenant Provisioned',
        `Created "${newOrg.name}" and sent initial credentials to ${formData.admin_email}.`
      );
      setIsModalOpen(false);
      setFormData({
        name: '',
        slug: '',
        admin_email: '',
        admin_name: '',
        admin_password: '',
        business_timezone: 'Asia/Kolkata',
        leap_day_policy: 'feb28',
      });
      fetchOrganizations();
    } catch (err: any) {
      toast.error('Provisioning Failed', err.message);
    } finally {
      setSubmitting(false);
    }
  };

  const handleToggleStatus = async (org: SuperAdminOrg) => {
    const newStatus = !org.is_active;
    try {
      await api.toggleOrganizationStatus(org.id, newStatus);
      toast.success(
        'Status Updated',
        `Organization "${org.name}" is now ${newStatus ? 'active' : 'suspended'}.`
      );
      fetchOrganizations();
    } catch (err: any) {
      toast.error('Failed to update status', err.message);
    }
  };

  const handleSwitchTenant = (org: SuperAdminOrg) => {
    switchTenant(org.id, org as any);
    toast.info('Switched Tenant Context', `Now managing "${org.name}".`);
    onSwitchToTenant();
  };

  const openResetPasswordModal = (org: SuperAdminOrg) => {
    setResettingOrg(org);
    setNewTenantPassword('');
    setIsResetModalOpen(true);
  };

  const handleResetPassword = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!resettingOrg || !newTenantPassword.trim()) return;
    if (newTenantPassword.length < 8) {
      toast.error('Invalid Password', 'New password must be at least 8 characters long.');
      return;
    }

    setResettingPassword(true);
    try {
      const res = await api.resetTenantPassword(resettingOrg.id, newTenantPassword);
      toast.success('Password Reset', res.message || `Password reset for ${resettingOrg.name}`);
      setIsResetModalOpen(false);
      setNewTenantPassword('');
      setResettingOrg(null);
    } catch (err: any) {
      toast.error('Reset Failed', err.message);
    } finally {
      setResettingPassword(false);
    }
  };

  const handleDeleteOrg = async (org: SuperAdminOrg) => {
    if (
      !window.confirm(
        `Are you sure you want to permanently delete "${org.name}"? All employees, events, templates, and delivery settings for this tenant will be permanently removed.`
      )
    ) {
      return;
    }
    try {
      await api.deleteOrganization(org.id);
      toast.success('Organization Deleted', `"${org.name}" has been permanently deleted.`);
      fetchOrganizations();
    } catch (err: any) {
      toast.error('Deletion Failed', err.message);
    }
  };

  const copyKey = (org: SuperAdminOrg) => {
    navigator.clipboard.writeText(org.api_key);
    setCopiedKeyId(org.id);
    setTimeout(() => setCopiedKeyId(null), 2000);
    toast.info('Copied', `API key for ${org.name} copied.`);
  };

  const totalEmployees = orgs.reduce((acc, o) => acc + o.employee_count, 0);
  const totalEvents = orgs.reduce((acc, o) => acc + o.event_count, 0);

  return (
    <div className="space-y-6">
      {/* Platform Header */}
      <div className="p-6 rounded-2xl bg-gradient-to-r from-purple-900 via-indigo-900 to-slate-900 border border-purple-800/40 shadow-xl text-white flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="inline-flex items-center gap-2 px-2.5 py-1 rounded-full bg-purple-500/20 border border-purple-400/30 text-purple-200 text-[11px] font-semibold mb-2">
            <Crown className="w-3.5 h-3.5 text-purple-400" />
            <span>Platform SuperAdmin Control Hub</span>
          </div>
          <h2 className="text-xl font-extrabold tracking-tight">Client Tenant Management</h2>
          <p className="text-xs text-purple-200/80 mt-0.5">
            Overview of all active client organizations, employee rosters, and system delivery metrics.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={fetchOrganizations}
            className="p-2.5 rounded-xl border border-white/10 bg-white/5 hover:bg-white/10 text-white text-xs font-semibold transition-colors"
            title="Refresh List"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
          </button>
          <button
            type="button"
            onClick={() => setIsModalOpen(true)}
            className="inline-flex items-center gap-1.5 px-4 py-2.5 rounded-xl bg-purple-500 hover:bg-purple-400 text-white text-xs font-semibold shadow-lg shadow-purple-500/30 transition-all active:scale-98"
          >
            <Plus className="w-4 h-4" />
            <span>Provision New Tenant</span>
          </button>
        </div>
      </div>

      {/* Metric Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <div className="p-5 rounded-2xl bg-white border border-slate-100 shadow-sm flex items-center gap-4">
          <div className="w-12 h-12 rounded-xl bg-purple-50 text-purple-600 flex items-center justify-center shrink-0">
            <Building className="w-6 h-6" />
          </div>
          <div>
            <p className="text-2xl font-extrabold text-slate-900">{orgs.length}</p>
            <p className="text-xs font-medium text-slate-500">Client Organizations</p>
          </div>
        </div>

        <div className="p-5 rounded-2xl bg-white border border-slate-100 shadow-sm flex items-center gap-4">
          <div className="w-12 h-12 rounded-xl bg-sky-50 text-sky-600 flex items-center justify-center shrink-0">
            <Users className="w-6 h-6" />
          </div>
          <div>
            <p className="text-2xl font-extrabold text-slate-900">{totalEmployees}</p>
            <p className="text-xs font-medium text-slate-500">Total Tracked Employees</p>
          </div>
        </div>

        <div className="p-5 rounded-2xl bg-white border border-slate-100 shadow-sm flex items-center gap-4">
          <div className="w-12 h-12 rounded-xl bg-emerald-50 text-emerald-600 flex items-center justify-center shrink-0">
            <CalendarCheck className="w-6 h-6" />
          </div>
          <div>
            <p className="text-2xl font-extrabold text-slate-900">{totalEvents}</p>
            <p className="text-xs font-medium text-slate-500">Total Celebrations Delivered</p>
          </div>
        </div>
      </div>

      {/* Tenant Directory Table */}
      <div className="rounded-2xl bg-white border border-slate-100 shadow-sm overflow-hidden">
        <div className="p-5 border-b border-slate-100 flex items-center justify-between">
          <div>
            <h3 className="text-sm font-bold text-slate-900">Provisioned Client Tenants</h3>
            <p className="text-xs text-slate-500">Click &quot;Switch to Tenant&quot; to manage any company as SuperAdmin</p>
          </div>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse text-xs">
            <thead>
              <tr className="bg-slate-50/80 text-slate-500 uppercase tracking-wider text-[10px] font-semibold border-b border-slate-100">
                <th className="py-3.5 px-4">Organization</th>
                <th className="py-3.5 px-4">Timezone</th>
                <th className="py-3.5 px-4 text-center">Employees</th>
                <th className="py-3.5 px-4 text-center">Events Sent</th>
                <th className="py-3.5 px-4 text-center">Status</th>
                <th className="py-3.5 px-4 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {orgs.map((org) => (
                <tr key={org.id} className="hover:bg-slate-50/60 transition-colors">
                  <td className="py-3.5 px-4">
                    <div className="flex items-center gap-3">
                      <div className="w-9 h-9 rounded-xl bg-slate-100 border border-slate-200 flex items-center justify-center font-bold text-slate-700 uppercase">
                        {org.name.substring(0, 2)}
                      </div>
                      <div>
                        <div className="flex items-center gap-2">
                          <span className="font-bold text-slate-900">{org.name}</span>
                          {org.is_demo && (
                            <span className="px-1.5 py-0.5 rounded bg-amber-100 text-amber-800 text-[10px] font-semibold">
                              Demo Sandbox
                            </span>
                          )}
                        </div>
                        <div className="flex items-center gap-2 text-[11px] text-slate-400 mt-0.5">
                          <span>slug: {org.slug}</span>
                          <span>•</span>
                          <button
                            type="button"
                            onClick={() => copyKey(org)}
                            className="text-slate-500 hover:text-slate-800 inline-flex items-center gap-1 font-mono"
                          >
                            {copiedKeyId === org.id ? (
                              <CheckCircle2 className="w-3 h-3 text-emerald-600" />
                            ) : (
                              <Copy className="w-3 h-3" />
                            )}
                            <span>{org.api_key.substring(0, 10)}...</span>
                          </button>
                        </div>
                      </div>
                    </div>
                  </td>

                  <td className="py-3.5 px-4 text-slate-600">
                    <span className="inline-flex items-center gap-1 font-mono text-[11px]">
                      <Clock className="w-3 h-3 text-slate-400" />
                      {org.business_timezone}
                    </span>
                  </td>

                  <td className="py-3.5 px-4 text-center font-semibold text-slate-800">
                    {org.employee_count}
                  </td>

                  <td className="py-3.5 px-4 text-center font-semibold text-slate-800">
                    {org.event_count}
                  </td>

                  <td className="py-3.5 px-4 text-center">
                    <span
                      className={`inline-flex items-center px-2.5 py-1 rounded-full text-[10px] font-bold ${
                        org.is_active
                          ? 'bg-emerald-50 text-emerald-700 border border-emerald-200'
                          : 'bg-rose-50 text-rose-700 border border-rose-200'
                      }`}
                    >
                      {org.is_active ? 'Active' : 'Suspended'}
                    </span>
                  </td>

                  <td className="py-3.5 px-4 text-right">
                    <div className="flex items-center justify-end gap-2">
                      <button
                        type="button"
                        onClick={() => handleToggleStatus(org)}
                        className="p-1.5 rounded-lg border border-slate-200 text-slate-500 hover:text-slate-800 hover:bg-slate-100 transition-colors"
                        title={org.is_active ? 'Suspend Tenant' : 'Activate Tenant'}
                      >
                        <Power className={`w-3.5 h-3.5 ${org.is_active ? 'text-rose-500' : 'text-emerald-500'}`} />
                      </button>

                      <button
                        type="button"
                        onClick={() => openResetPasswordModal(org)}
                        className="p-1.5 rounded-lg border border-slate-200 text-slate-500 hover:text-amber-600 hover:bg-amber-50 hover:border-amber-200 transition-colors"
                        title="Reset Tenant Admin Password"
                      >
                        <Key className="w-3.5 h-3.5 text-amber-500" />
                      </button>

                      <button
                        type="button"
                        onClick={() => handleDeleteOrg(org)}
                        className="p-1.5 rounded-lg border border-slate-200 text-slate-400 hover:text-rose-600 hover:bg-rose-50 hover:border-rose-200 transition-colors"
                        title="Permanently Delete Organization"
                      >
                        <Trash2 className="w-3.5 h-3.5 text-rose-500" />
                      </button>

                      <button
                        type="button"
                        onClick={() => handleSwitchTenant(org)}
                        className="inline-flex items-center gap-1 px-3 py-1.5 rounded-lg bg-slate-900 hover:bg-slate-800 text-white font-semibold text-[11px] shadow-xs transition-colors"
                      >
                        <span>Manage</span>
                        <ExternalLink className="w-3 h-3" />
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Provision New Client Organization Modal */}
      <Modal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        title="Provision New Client Tenant"
        maxWidth="lg"
      >
        <form onSubmit={handleCreateTenant} className="space-y-4 text-xs">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="block font-semibold text-slate-700 mb-1">Company / Organization Name *</label>
              <input
                type="text"
                required
                placeholder="e.g. Globex Corporation"
                value={formData.name}
                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                className="w-full px-3 py-2 rounded-xl border border-slate-200 focus:outline-none focus:ring-2 focus:ring-purple-500/20 focus:border-purple-500"
              />
            </div>

            <div>
              <label className="block font-semibold text-slate-700 mb-1">URL Identifier (Slug)</label>
              <input
                type="text"
                placeholder="e.g. globex"
                value={formData.slug}
                onChange={(e) => setFormData({ ...formData, slug: e.target.value })}
                className="w-full px-3 py-2 rounded-xl border border-slate-200 focus:outline-none focus:ring-2 focus:ring-purple-500/20 focus:border-purple-500"
              />
            </div>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="block font-semibold text-slate-700 mb-1">Business Timezone *</label>
              <select
                value={formData.business_timezone}
                onChange={(e) => setFormData({ ...formData, business_timezone: e.target.value })}
                className="w-full px-3 py-2 rounded-xl border border-slate-200 focus:outline-none focus:ring-2 focus:ring-purple-500/20 focus:border-purple-500"
              >
                <option value="Asia/Kolkata">Asia/Kolkata (IST +5:30)</option>
                <option value="America/New_York">America/New_York (EST -5:00)</option>
                <option value="America/Los_Angeles">America/Los_Angeles (PST -8:00)</option>
                <option value="Europe/London">Europe/London (GMT +0:00)</option>
                <option value="Europe/Paris">Europe/Paris (CET +1:00)</option>
                <option value="Asia/Singapore">Asia/Singapore (SGT +8:00)</option>
                <option value="Asia/Dubai">Asia/Dubai (GST +4:00)</option>
              </select>
            </div>

            <div>
              <label className="block font-semibold text-slate-700 mb-1">Leap Day Celebration Policy</label>
              <select
                value={formData.leap_day_policy}
                onChange={(e) => setFormData({ ...formData, leap_day_policy: e.target.value })}
                className="w-full px-3 py-2 rounded-xl border border-slate-200 focus:outline-none focus:ring-2 focus:ring-purple-500/20 focus:border-purple-500"
              >
                <option value="feb28">Feb 28 in non-leap years</option>
                <option value="mar1">Mar 1 in non-leap years</option>
              </select>
            </div>
          </div>

          <div className="pt-2 border-t border-slate-100">
            <p className="font-bold text-slate-900 mb-3">Initial Tenant Administrator</p>
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
              <div>
                <label className="block font-semibold text-slate-700 mb-1">Admin Full Name *</label>
                <input
                  type="text"
                  required
                  placeholder="e.g. Hank Scorpio"
                  value={formData.admin_name}
                  onChange={(e) => setFormData({ ...formData, admin_name: e.target.value })}
                  className="w-full px-3 py-2 rounded-xl border border-slate-200 focus:outline-none focus:ring-2 focus:ring-purple-500/20 focus:border-purple-500"
                />
              </div>

              <div>
                <label className="block font-semibold text-slate-700 mb-1">Admin Email *</label>
                <input
                  type="email"
                  required
                  placeholder="hr@globex.com"
                  value={formData.admin_email}
                  onChange={(e) => setFormData({ ...formData, admin_email: e.target.value })}
                  className="w-full px-3 py-2 rounded-xl border border-slate-200 focus:outline-none focus:ring-2 focus:ring-purple-500/20 focus:border-purple-500"
                />
              </div>

              <div>
                <label className="block font-semibold text-slate-700 mb-1">Initial Password *</label>
                <input
                  type="password"
                  required
                  placeholder="••••••••"
                  value={formData.admin_password}
                  onChange={(e) => setFormData({ ...formData, admin_password: e.target.value })}
                  className="w-full px-3 py-2 rounded-xl border border-slate-200 focus:outline-none focus:ring-2 focus:ring-purple-500/20 focus:border-purple-500"
                />
              </div>
            </div>
          </div>

          <div className="flex items-center justify-end gap-2 pt-4 border-t border-slate-100">
            <button
              type="button"
              onClick={() => setIsModalOpen(false)}
              className="px-4 py-2 rounded-xl border border-slate-200 text-slate-700 font-semibold hover:bg-slate-100 transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={submitting}
              className="inline-flex items-center gap-1.5 px-5 py-2 rounded-xl bg-purple-600 hover:bg-purple-500 text-white font-semibold shadow-md transition-colors disabled:opacity-50"
            >
              <Sparkles className="w-4 h-4" />
              <span>{submitting ? 'Provisioning...' : 'Provision Tenant'}</span>
            </button>
          </div>
        </form>
      </Modal>

      {/* Reset Tenant Admin Password Modal */}
      <Modal
        isOpen={isResetModalOpen}
        onClose={() => {
          setIsResetModalOpen(false);
          setResettingOrg(null);
          setNewTenantPassword('');
        }}
        title={`Reset Admin Password: ${resettingOrg?.name || ''}`}
        maxWidth="md"
      >
        <form onSubmit={handleResetPassword} className="space-y-4 text-xs">
          <p className="text-slate-600">
            Set a new temporary or permanent password for the administrator of <strong className="text-slate-900">{resettingOrg?.name}</strong>.
          </p>

          <div>
            <label className="block font-semibold text-slate-700 mb-1">New Password (min 8 characters) *</label>
            <input
              type="password"
              required
              placeholder="••••••••"
              value={newTenantPassword}
              onChange={(e) => setNewTenantPassword(e.target.value)}
              className="w-full px-3 py-2 rounded-xl border border-slate-200 focus:outline-none focus:ring-2 focus:ring-purple-500/20 focus:border-purple-500"
            />
          </div>

          <div className="flex items-center justify-end gap-2 pt-4 border-t border-slate-100">
            <button
              type="button"
              onClick={() => {
                setIsResetModalOpen(false);
                setResettingOrg(null);
                setNewTenantPassword('');
              }}
              className="px-4 py-2 rounded-xl border border-slate-200 text-slate-700 font-semibold hover:bg-slate-100 transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={resettingPassword || newTenantPassword.length < 8}
              className="inline-flex items-center gap-1.5 px-5 py-2 rounded-xl bg-amber-600 hover:bg-amber-500 text-white font-semibold shadow-md transition-colors disabled:opacity-50"
            >
              <Key className="w-4 h-4" />
              <span>{resettingPassword ? 'Resetting...' : 'Reset Password'}</span>
            </button>
          </div>
        </form>
      </Modal>
    </div>
  );
};
