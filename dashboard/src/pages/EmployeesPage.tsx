import React, { useEffect, useState } from 'react';
import { api } from '../api/client';
import { Employee, EmployeeCreatePayload, EmployeeDetail, EmployeeUpdatePayload, EventTemplate } from '../types';
import { Avatar } from '../components/common/Avatar';
import { Badge } from '../components/common/Badge';
import { Drawer } from '../components/common/Drawer';
import { Modal } from '../components/common/Modal';
import { CsvImportModal } from '../components/common/CsvImportModal';
import { Pagination } from '../components/common/Pagination';
import { EmptyState } from '../components/common/EmptyState';
import { TableSkeleton } from '../components/common/Skeleton';
import { useToast } from '../context/ToastContext';
import {
  Users,
  Search,
  Plus,
  Edit2,
  Mail,
  Building,
  RefreshCw,
  Clock,
  AlertCircle,
  X,
  UploadCloud,
  Camera,
  Sparkles,
  Upload,
} from 'lucide-react';
import { useAuth } from '../context/AuthContext';

interface EmployeesPageProps {
  onNavigateTab?: (tab: 'events' | 'employees' | 'digests' | 'templates' | 'superadmin' | 'settings') => void;
}

export const EmployeesPage: React.FC<EmployeesPageProps> = ({ onNavigateTab }) => {
  const { activeOrg } = useAuth();
  const isSetupIncomplete = Boolean(activeOrg && (!activeOrg.is_db_configured || !activeOrg.is_setup_complete));
  const [employees, setEmployees] = useState<Employee[]>([]);
  const [total, setTotal] = useState(0);
  const [limit, setLimit] = useState(25);
  const [offset, setOffset] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Filters
  const [search, setSearch] = useState('');
  const [isActiveFilter, setIsActiveFilter] = useState<string>('');

  // Modals & Drawers
  const [selectedEmployee, setSelectedEmployee] = useState<EmployeeDetail | null>(null);
  const [isDrawerOpen, setIsDrawerOpen] = useState(false);
  const [drawerLoading, setDrawerLoading] = useState(false);

  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);
  const [isEditModalOpen, setIsEditModalOpen] = useState(false);
  const [isCsvModalOpen, setIsCsvModalOpen] = useState(false);
  const [editingEmployee, setEditingEmployee] = useState<Employee | null>(null);
  const [availableTemplates, setAvailableTemplates] = useState<EventTemplate[]>([]);

  useEffect(() => {
    api.getTemplates().then(setAvailableTemplates).catch(() => {});
  }, []);

  // Form State
  const [formData, setFormData] = useState<EmployeeCreatePayload>({
    employee_code: '',
    full_name: '',
    preferred_name: '',
    email: '',
    photo_url: '',
    date_of_birth: '',
    date_of_joining: '',
    department: '',
    team_channel_id: '',
    birthday_template_id: null,
    anniversary_template_id: null,
    is_active: true,
  });
  const [formSubmitting, setFormSubmitting] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);

  const toast = useToast();

  const fetchEmployees = async () => {
    setLoading(true);
    setError(null);
    try {
      const activeParam = isActiveFilter === '' ? undefined : isActiveFilter === 'true';
      const data = await api.getEmployees({
        search: search.trim() || undefined,
        is_active: activeParam,
        limit,
        offset,
      });
      setEmployees(data.items);
      setTotal(data.total);
    } catch (err: any) {
      const message = err.message || 'Failed to load employees';
      setError(message);
      if (err.status === 403 || err.status === 503) toast.warning('Tenant database needs attention', message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchEmployees();
  }, [offset, limit, isActiveFilter]);

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setOffset(0);
    fetchEmployees();
  };

  const handleRowClick = async (emp: Employee) => {
    setIsDrawerOpen(true);
    setDrawerLoading(true);
    try {
      const detail = await api.getEmployee(emp.id);
      setSelectedEmployee(detail);
    } catch (err: any) {
      toast.error('Failed to load employee details', err.message);
    } finally {
      setDrawerLoading(false);
    }
  };

  const [requestingPhotoId, setRequestingPhotoId] = useState<string | null>(null);
  const [uploadingPhotoId, setUploadingPhotoId] = useState<string | null>(null);
  const drawerPhotoInputRef = React.useRef<HTMLInputElement>(null);

  const handleRequestPhoto = async (emp: Employee, e?: React.MouseEvent) => {
    if (e) e.stopPropagation();
    setRequestingPhotoId(emp.id);
    try {
      const res = await api.requestEmployeePhoto(emp.id);
      toast.success('Photo Request Sent', res.message);
      fetchEmployees();
      if (selectedEmployee && selectedEmployee.id === emp.id) {
        setSelectedEmployee({
          ...selectedEmployee,
          photo_request_sent_at: new Date().toISOString(),
        });
      }
    } catch (err: any) {
      toast.error('Failed to Send Request', err.message);
    } finally {
      setRequestingPhotoId(null);
    }
  };

  const handleDirectPhotoUpload = async (emp: Employee, file: File) => {
    setUploadingPhotoId(emp.id);
    try {
      const updated = await api.uploadEmployeePhoto(emp.id, file);
      toast.success('Photo Uploaded', `Custom celebration photo saved for ${emp.full_name}!`);
      fetchEmployees();
      if (selectedEmployee && selectedEmployee.id === emp.id) {
        setSelectedEmployee({
          ...selectedEmployee,
          photo_url: updated.photo_url,
          has_custom_photo: true,
        });
      }
    } catch (err: any) {
      toast.error('Photo Upload Failed', err.message);
    } finally {
      setUploadingPhotoId(null);
    }
  };

  const openCreateModal = () => {
    setFormData({
      employee_code: '',
      full_name: '',
      preferred_name: '',
      email: '',
      photo_url: '',
      date_of_birth: '',
      date_of_joining: '',
      department: '',
      team_channel_id: '',
      birthday_template_id: null,
      anniversary_template_id: null,
      is_active: true,
    });
    api.getTemplates().then(setAvailableTemplates).catch(() => {});
    setFormError(null);
    setIsCreateModalOpen(true);
  };

  const openEditModal = (emp: Employee, e?: React.MouseEvent) => {
    if (e) e.stopPropagation();
    setEditingEmployee(emp);
    setFormData({
      employee_code: emp.employee_code,
      full_name: emp.full_name,
      preferred_name: emp.preferred_name || '',
      email: emp.email,
      photo_url: emp.photo_url || '',
      date_of_birth: emp.date_of_birth || '',
      date_of_joining: emp.date_of_joining || '',
      department: emp.department || '',
      team_channel_id: emp.team_channel_id || '',
      birthday_template_id: emp.birthday_template_id || null,
      anniversary_template_id: emp.anniversary_template_id || null,
      is_active: emp.is_active,
    });
    api.getTemplates().then(setAvailableTemplates).catch(() => {});
    setFormError(null);
    setIsEditModalOpen(true);
  };

  const handleCreateSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setFormSubmitting(true);
    setFormError(null);

    // Client-side validation
    if (!formData.employee_code.trim() || !formData.full_name.trim() || !formData.email.trim()) {
      setFormError('Employee code, full name, and email are required.');
      setFormSubmitting(false);
      return;
    }

    try {
      const payload: EmployeeCreatePayload = {
        employee_code: formData.employee_code.trim(),
        full_name: formData.full_name.trim(),
        preferred_name: formData.preferred_name?.trim() || null,
        email: formData.email.trim(),
        photo_url: formData.photo_url?.trim() || null,
        date_of_birth: formData.date_of_birth || null,
        date_of_joining: formData.date_of_joining || null,
        department: formData.department?.trim() || null,
        team_channel_id: formData.team_channel_id?.trim() || null,
        birthday_template_id: formData.birthday_template_id || null,
        anniversary_template_id: formData.anniversary_template_id || null,
        is_active: formData.is_active,
      };

      await api.createEmployee(payload);
      toast.success('Employee Created', `${payload.full_name} was added successfully.`);
      setIsCreateModalOpen(false);
      fetchEmployees();
    } catch (err: any) {
      setFormError(err.message || 'Failed to create employee');
    } finally {
      setFormSubmitting(false);
    }
  };

  const handleEditSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!editingEmployee) return;

    setFormSubmitting(true);
    setFormError(null);

    try {
      const payload: EmployeeUpdatePayload = {
        employee_code: formData.employee_code.trim(),
        full_name: formData.full_name.trim(),
        preferred_name: formData.preferred_name?.trim() || null,
        email: formData.email.trim(),
        photo_url: formData.photo_url?.trim() || null,
        date_of_birth: formData.date_of_birth || null,
        date_of_joining: formData.date_of_joining || null,
        department: formData.department?.trim() || null,
        team_channel_id: formData.team_channel_id?.trim() || null,
        birthday_template_id: formData.birthday_template_id || null,
        anniversary_template_id: formData.anniversary_template_id || null,
        is_active: formData.is_active,
      };

      await api.updateEmployee(editingEmployee.id, payload);
      toast.success('Employee Updated', `${payload.full_name} was updated successfully.`);
      setIsEditModalOpen(false);
      fetchEmployees();
      if (selectedEmployee && selectedEmployee.id === editingEmployee.id) {
        const fresh = await api.getEmployee(editingEmployee.id);
        setSelectedEmployee(fresh);
      }
    } catch (err: any) {
      setFormError(err.message || 'Failed to update employee');
    } finally {
      setFormSubmitting(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Onboarding Warning Banner if Setup Incomplete */}
      {isSetupIncomplete && (
        <div className="p-4 rounded-2xl bg-amber-50 border border-amber-200 text-amber-900 flex flex-col sm:flex-row sm:items-center justify-between gap-3 shadow-sm">
          <div className="flex items-start sm:items-center gap-3">
            <AlertCircle className="w-5 h-5 text-amber-600 shrink-0 mt-0.5 sm:mt-0" />
            <div className="text-xs">
              <p className="font-bold text-amber-950">
                You cannot add your data before you configure your database and email provider service.
              </p>
              <p className="text-amber-800 mt-0.5">
                Connect your private PostgreSQL database and verified SMTP email provider in Settings to unlock adding or importing employee records.
              </p>
            </div>
          </div>
          {onNavigateTab && (
            <button
              type="button"
              onClick={() => onNavigateTab('settings')}
              className="inline-flex items-center gap-1.5 px-3.5 py-1.5 rounded-xl bg-amber-600 hover:bg-amber-700 text-white text-xs font-semibold shrink-0 cursor-pointer shadow-sm transition-colors"
            >
              <span>Configure in Settings →</span>
            </button>
          )}
        </div>
      )}

      {/* Top Header & Search / Filter */}
      <div className="p-5 rounded-2xl bg-white border border-slate-100 shadow-sm space-y-4">
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
          <div>
            <h3 className="text-base font-bold text-slate-800">Employee Directory</h3>
            <p className="text-xs text-slate-500 mt-0.5">
              Local mirror of employees used for birthday and work anniversary milestone detection
            </p>
          </div>
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={fetchEmployees}
              className="p-2 rounded-xl border border-slate-200 bg-white hover:bg-slate-50 text-slate-700 text-xs font-semibold shadow-xs transition-colors cursor-pointer"
              title="Refresh Directory"
            >
              <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
            </button>
            <button
              type="button"
              onClick={() => {
                if (isSetupIncomplete) {
                  toast.error('Setup Required', 'You cannot add your data before you configure your database and email provider service.');
                  return;
                }
                setIsCsvModalOpen(true);
              }}
              disabled={isSetupIncomplete}
              title={isSetupIncomplete ? 'You cannot add your data before you configure your database and email provider service.' : 'Import CSV'}
              className={`inline-flex items-center gap-1.5 px-4 py-2 rounded-xl border border-slate-200 bg-white text-slate-700 text-xs font-semibold shadow-xs transition-colors ${
                isSetupIncomplete ? 'opacity-50 cursor-not-allowed' : 'hover:bg-slate-50 cursor-pointer'
              }`}
            >
              <UploadCloud className="w-4 h-4 text-rose-500" />
              <span>Import CSV</span>
            </button>
            <button
              type="button"
              onClick={() => {
                if (isSetupIncomplete) {
                  toast.error('Setup Required', 'You cannot add your data before you configure your database and email provider service.');
                  return;
                }
                openCreateModal();
              }}
              disabled={isSetupIncomplete}
              title={isSetupIncomplete ? 'You cannot add your data before you configure your database and email provider service.' : 'Add Employee'}
              className={`inline-flex items-center gap-1.5 px-4 py-2 rounded-xl bg-slate-900 text-white text-xs font-semibold shadow-sm transition-colors ${
                isSetupIncomplete ? 'opacity-50 cursor-not-allowed' : 'hover:bg-slate-800 cursor-pointer'
              }`}
            >
              <Plus className="w-4 h-4" />
              <span>Add Employee</span>
            </button>
          </div>
        </div>

        {/* Filter Bar */}
        <form onSubmit={handleSearchSubmit} className="grid grid-cols-1 sm:grid-cols-3 lg:grid-cols-4 gap-3 pt-2 border-t border-slate-100">
          <div className="relative sm:col-span-2">
            <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-slate-400">
              <Search className="w-4 h-4" />
            </div>
            <input
              type="text"
              placeholder="Search by name, email, employee code, department..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="w-full pl-9 pr-3 py-2 text-xs rounded-xl border border-slate-200 bg-white text-slate-800 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-rose-500/20 focus:border-rose-500"
            />
          </div>

          <div>
            <select
              value={isActiveFilter}
              onChange={(e) => {
                setIsActiveFilter(e.target.value);
                setOffset(0);
              }}
              className="w-full px-3 py-2 text-xs rounded-xl border border-slate-200 bg-white text-slate-800 focus:outline-none focus:ring-2 focus:ring-rose-500/20 focus:border-rose-500 cursor-pointer"
            >
              <option value="">All Statuses</option>
              <option value="true">Active Staff Only</option>
              <option value="false">Inactive Staff Only</option>
            </select>
          </div>

          <div className="flex items-center gap-2">
            <button
              type="submit"
              className="px-4 py-2 bg-slate-100 hover:bg-slate-200 text-slate-800 rounded-xl text-xs font-semibold transition-colors"
            >
              Search
            </button>
            {(search || isActiveFilter !== '') && (
              <button
                type="button"
                onClick={() => {
                  setSearch('');
                  setIsActiveFilter('');
                  setOffset(0);
                  setTimeout(fetchEmployees, 0);
                }}
                className="p-2 text-slate-400 hover:text-slate-700"
                title="Clear Search"
              >
                <X className="w-4 h-4" />
              </button>
            )}
          </div>
        </form>
      </div>

      {/* Employees Table */}
      <div className="rounded-2xl bg-white border border-slate-100 shadow-sm overflow-hidden">
        {loading ? (
          <TableSkeleton rows={8} cols={7} />
        ) : error ? (
          <div className="p-8 text-center text-rose-600 text-xs">
            <AlertCircle className="w-8 h-8 mx-auto mb-2 text-rose-500" />
            <p className="font-semibold">{error}</p>
          </div>
        ) : employees.length === 0 ? (
          <EmptyState
            icon={Users}
            title="No employees found"
            description="No employee records match your search criteria. Add an employee manually or trigger an HRMS sync."
            action={{
              label: 'Add First Employee',
              onClick: openCreateModal,
            }}
          />
        ) : (
          <>
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs text-slate-600">
                <thead className="bg-slate-50/80 border-b border-slate-100 text-[11px] uppercase tracking-wider font-semibold text-slate-500">
                  <tr>
                    <th className="px-4 py-3.5">Employee</th>
                    <th className="px-4 py-3.5">Code</th>
                    <th className="px-4 py-3.5">Department</th>
                    <th className="px-4 py-3.5">Date of Birth</th>
                    <th className="px-4 py-3.5">Date of Joining</th>
                    <th className="px-4 py-3.5">Status</th>
                    <th className="px-4 py-3.5 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {employees.map((emp) => (
                    <tr
                      key={emp.id}
                      onClick={() => handleRowClick(emp)}
                      className="hover:bg-slate-50/80 cursor-pointer transition-colors group"
                    >
                      {/* Name & Photo */}
                      <td className="px-4 py-3.5 whitespace-nowrap">
                        <div className="flex items-center gap-3">
                          <Avatar name={emp.preferred_name || emp.full_name} photoUrl={emp.photo_url} size="md" />
                          <div>
                            <div className="font-semibold text-slate-800">
                              {emp.full_name}
                              {emp.preferred_name && (
                                <span className="ml-1 text-slate-400 font-normal">
                                  ({emp.preferred_name})
                                </span>
                              )}
                            </div>
                            <div className="text-[11px] text-slate-400 flex items-center gap-1">
                              <Mail className="w-3 h-3 text-slate-400" />
                              <span>{emp.email}</span>
                            </div>
                            <div className="pt-0.5">
                              {emp.has_custom_photo ? (
                                <span className="inline-flex items-center gap-1 text-[10px] font-semibold text-rose-600 bg-rose-50 px-1.5 py-0.5 rounded border border-rose-200">
                                  <Camera className="w-2.5 h-2.5" />
                                  Custom Photo
                                </span>
                              ) : (
                                <span className="inline-flex items-center gap-1 text-[10px] text-slate-400 bg-slate-100 px-1.5 py-0.5 rounded">
                                  Default Avatar
                                </span>
                              )}
                            </div>
                          </div>
                        </div>
                      </td>

                      {/* Code */}
                      <td className="px-4 py-3.5 font-mono font-medium text-slate-700 whitespace-nowrap">
                        {emp.employee_code}
                      </td>

                      {/* Department */}
                      <td className="px-4 py-3.5 whitespace-nowrap">
                        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md bg-slate-100 text-slate-700 text-[11px]">
                          <Building className="w-3 h-3 text-slate-400" />
                          <span>{emp.department || 'General'}</span>
                        </span>
                      </td>

                      {/* DOB */}
                      <td className="px-4 py-3.5 whitespace-nowrap font-mono text-slate-700">
                        {emp.date_of_birth || '—'}
                      </td>

                      {/* DOJ */}
                      <td className="px-4 py-3.5 whitespace-nowrap font-mono text-slate-700">
                        {emp.date_of_joining || '—'}
                      </td>

                      {/* Active Status */}
                      <td className="px-4 py-3.5 whitespace-nowrap">
                        <Badge status={emp.is_active ? 'active' : 'inactive'} />
                      </td>

                      {/* Actions */}
                      <td className="px-4 py-3.5 text-right whitespace-nowrap" onClick={(e) => e.stopPropagation()}>
                        <div className="flex items-center justify-end gap-1">
                          <button
                            type="button"
                            onClick={(e) => handleRequestPhoto(emp, e)}
                            disabled={requestingPhotoId === emp.id}
                            className="p-1.5 rounded-lg text-slate-400 hover:text-rose-600 hover:bg-rose-50 transition-colors cursor-pointer"
                            title="Send Celebration Photo Request Email"
                          >
                            <Camera className={`w-3.5 h-3.5 ${requestingPhotoId === emp.id ? 'animate-spin' : ''}`} />
                          </button>
                          <button
                            type="button"
                            onClick={(e) => openEditModal(emp, e)}
                            className="p-1.5 rounded-lg text-slate-400 hover:text-slate-700 hover:bg-slate-100 transition-colors cursor-pointer"
                            title="Edit Profile"
                          >
                            <Edit2 className="w-3.5 h-3.5" />
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            <Pagination
              total={total}
              limit={limit}
              offset={offset}
              onPageChange={(newOffset) => setOffset(newOffset)}
              onLimitChange={(newLimit) => {
                setLimit(newLimit);
                setOffset(0);
              }}
            />
          </>
        )}
      </div>

      {/* Employee Detail Drawer */}
      <Drawer
        isOpen={isDrawerOpen}
        onClose={() => setIsDrawerOpen(false)}
        title={selectedEmployee ? selectedEmployee.full_name : 'Employee Profile'}
        subtitle={selectedEmployee ? `Code: ${selectedEmployee.employee_code}` : ''}
        width="xl"
      >
        {drawerLoading ? (
          <TableSkeleton rows={5} cols={3} />
        ) : selectedEmployee ? (
          <div className="space-y-6">
            {/* Header Profile Summary */}
            <div className="flex items-start justify-between p-4 rounded-2xl bg-slate-50 border border-slate-200/80">
              <div className="flex items-center gap-4">
                <Avatar
                  name={selectedEmployee.preferred_name || selectedEmployee.full_name}
                  photoUrl={selectedEmployee.photo_url}
                  size="xl"
                />
                <div className="space-y-1">
                  <h4 className="text-base font-bold text-slate-900">
                    {selectedEmployee.full_name}
                  </h4>
                  {selectedEmployee.preferred_name && (
                    <div className="text-xs text-slate-500">
                      Preferred: <span className="font-semibold text-slate-700">{selectedEmployee.preferred_name}</span>
                    </div>
                  )}
                  <div className="flex items-center gap-2 pt-1">
                    <Badge status={selectedEmployee.is_active ? 'active' : 'inactive'} size="sm" />
                    <span className="text-xs text-slate-500 font-mono">
                      {selectedEmployee.employee_code}
                    </span>
                  </div>
                </div>
              </div>

              <button
                type="button"
                onClick={() => openEditModal(selectedEmployee)}
                className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl border border-slate-200 bg-white hover:bg-slate-100 text-slate-700 text-xs font-semibold transition-colors"
              >
                <Edit2 className="w-3.5 h-3.5" />
                <span>Edit</span>
              </button>
            </div>

            {/* Celebration Photo & Request Card */}
            <div className="p-4 rounded-2xl bg-white border border-slate-200 space-y-3">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Camera className="w-4 h-4 text-rose-500" />
                  <h5 className="text-xs font-bold text-slate-800">Celebration Photo Status</h5>
                </div>
                {selectedEmployee.has_custom_photo ? (
                  <span className="inline-flex items-center gap-1 text-[11px] font-semibold text-rose-700 bg-rose-50 px-2 py-0.5 rounded-full border border-rose-200">
                    <Sparkles className="w-3 h-3 text-rose-500" />
                    Custom Chosen Photo
                  </span>
                ) : (
                  <span className="inline-flex items-center gap-1 text-[11px] text-slate-500 bg-slate-100 px-2 py-0.5 rounded-full">
                    Default Company Avatar
                  </span>
                )}
              </div>

              <p className="text-xs text-slate-500 leading-relaxed">
                {selectedEmployee.has_custom_photo
                  ? 'This employee has submitted a personal photo. It will be featured in celebratory emails and team digests.'
                  : 'No custom photo submitted yet. Celebrations will use the standard default template.'}
              </p>

              {selectedEmployee.photo_request_sent_at && (
                <p className="text-[11px] text-slate-400">
                  Last photo request email sent: {new Date(selectedEmployee.photo_request_sent_at).toLocaleDateString()}
                </p>
              )}

              <div className="flex items-center gap-2 pt-1">
                <button
                  type="button"
                  onClick={() => handleRequestPhoto(selectedEmployee)}
                  disabled={requestingPhotoId === selectedEmployee.id}
                  className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-rose-50 hover:bg-rose-100 text-rose-700 border border-rose-200 text-xs font-semibold transition-colors cursor-pointer"
                >
                  <Mail className={`w-3.5 h-3.5 ${requestingPhotoId === selectedEmployee.id ? 'animate-spin' : ''}`} />
                  <span>{requestingPhotoId === selectedEmployee.id ? 'Sending Request...' : 'Send Photo Request Email'}</span>
                </button>

                <input
                  ref={drawerPhotoInputRef}
                  type="file"
                  accept="image/jpeg,image/png,image/webp,image/gif"
                  onChange={(e) => {
                    if (e.target.files && e.target.files[0]) {
                      handleDirectPhotoUpload(selectedEmployee, e.target.files[0]);
                    }
                  }}
                  className="hidden"
                />

                <button
                  type="button"
                  onClick={() => drawerPhotoInputRef.current?.click()}
                  disabled={uploadingPhotoId === selectedEmployee.id}
                  className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl border border-slate-200 hover:bg-slate-50 text-slate-700 text-xs font-semibold transition-colors cursor-pointer"
                >
                  <Upload className={`w-3.5 h-3.5 ${uploadingPhotoId === selectedEmployee.id ? 'animate-spin' : ''}`} />
                  <span>{uploadingPhotoId === selectedEmployee.id ? 'Uploading...' : 'Upload Photo Now'}</span>
                </button>
              </div>
            </div>

            {/* Profile Fields Details */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs">
              <div className="p-3.5 rounded-xl bg-white border border-slate-200 space-y-1">
                <div className="text-[10px] uppercase font-semibold text-slate-400">Email Address</div>
                <div className="font-semibold text-slate-800 flex items-center gap-1.5">
                  <Mail className="w-3.5 h-3.5 text-slate-400" />
                  <span>{selectedEmployee.email}</span>
                </div>
              </div>

              <div className="p-3.5 rounded-xl bg-white border border-slate-200 space-y-1">
                <div className="text-[10px] uppercase font-semibold text-slate-400">Department</div>
                <div className="font-semibold text-slate-800 flex items-center gap-1.5">
                  <Building className="w-3.5 h-3.5 text-slate-400" />
                  <span>{selectedEmployee.department || 'Not Assigned'}</span>
                </div>
              </div>

              <div className="p-3.5 rounded-xl bg-white border border-slate-200 space-y-1">
                <div className="text-[10px] uppercase font-semibold text-slate-400">Date of Birth (DOB)</div>
                <div className="font-semibold text-slate-800 font-mono">
                  {selectedEmployee.date_of_birth || 'Not Recorded'}
                </div>
              </div>

              <div className="p-3.5 rounded-xl bg-white border border-slate-200 space-y-1">
                <div className="text-[10px] uppercase font-semibold text-slate-400">Date of Joining (DOJ)</div>
                <div className="font-semibold text-slate-800 font-mono">
                  {selectedEmployee.date_of_joining || 'Not Recorded'}
                </div>
              </div>
            </div>

            {/* Recent Event History */}
            <div className="space-y-3 pt-2">
              <h5 className="text-xs font-bold uppercase tracking-wider text-slate-700 flex items-center gap-1.5">
                <Clock className="w-4 h-4 text-slate-400" />
                <span>Recent Celebration History</span>
              </h5>

              {selectedEmployee.recent_events.length === 0 ? (
                <div className="p-6 rounded-xl bg-slate-50 border border-dashed border-slate-200 text-center text-slate-400 text-xs">
                  No celebrations have run for this employee yet.
                </div>
              ) : (
                <div className="divide-y divide-slate-100 rounded-xl border border-slate-200 bg-white overflow-hidden">
                  {selectedEmployee.recent_events.map((ev) => (
                    <div key={ev.id} className="p-3.5 flex items-center justify-between text-xs hover:bg-slate-50 transition-colors">
                      <div className="space-y-0.5">
                        <div className="flex items-center gap-2">
                          <Badge eventType={ev.event_type} size="sm" />
                          <span className="font-mono text-slate-700 font-semibold">{ev.event_date}</span>
                          {ev.years && (
                            <span className="text-[11px] font-semibold text-purple-700 bg-purple-50 px-1.5 rounded">
                              {ev.years} yr{ev.years > 1 ? 's' : ''}
                            </span>
                          )}
                        </div>
                        <div className="text-slate-500 text-[11px] truncate max-w-sm">
                          {ev.rendered_subject || 'Pending render'}
                        </div>
                      </div>

                      <div className="text-right">
                        <Badge status={ev.status} size="sm" />
                        {ev.sent_at && (
                          <div className="text-[10px] text-slate-400 mt-1">
                            {new Date(ev.sent_at).toLocaleDateString()}
                          </div>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        ) : null}
      </Drawer>

      {/* Add Employee Modal */}
      <Modal
        isOpen={isCreateModalOpen}
        onClose={() => setIsCreateModalOpen(false)}
        title="Add New Employee Profile"
        subtitle="Manually create an employee record before HRMS sync is connected"
        maxWidth="2xl"
      >
        <form onSubmit={handleCreateSubmit} className="space-y-4">
          {formError && (
            <div className="p-3 rounded-xl bg-rose-50 border border-rose-200 text-xs text-rose-800">
              {formError}
            </div>
          )}

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-xs">
            <div>
              <label className="block font-semibold uppercase text-slate-700 mb-1">
                Employee Code <span className="text-rose-500">*</span>
              </label>
              <input
                type="text"
                required
                placeholder="e.g. EMP-042"
                value={formData.employee_code}
                onChange={(e) => setFormData({ ...formData, employee_code: e.target.value })}
                className="w-full px-3 py-2 rounded-xl border border-slate-200 focus:ring-2 focus:ring-rose-500/20 focus:border-rose-500 text-xs"
              />
            </div>

            <div>
              <label className="block font-semibold uppercase text-slate-700 mb-1">
                Full Name <span className="text-rose-500">*</span>
              </label>
              <input
                type="text"
                required
                placeholder="e.g. Jane Doe"
                value={formData.full_name}
                onChange={(e) => setFormData({ ...formData, full_name: e.target.value })}
                className="w-full px-3 py-2 rounded-xl border border-slate-200 focus:ring-2 focus:ring-rose-500/20 focus:border-rose-500 text-xs"
              />
            </div>

            <div>
              <label className="block font-semibold uppercase text-slate-700 mb-1">Preferred Name</label>
              <input
                type="text"
                placeholder="e.g. Jane"
                value={formData.preferred_name || ''}
                onChange={(e) => setFormData({ ...formData, preferred_name: e.target.value })}
                className="w-full px-3 py-2 rounded-xl border border-slate-200 focus:ring-2 focus:ring-rose-500/20 focus:border-rose-500 text-xs"
              />
            </div>

            <div>
              <label className="block font-semibold uppercase text-slate-700 mb-1">
                Email Address <span className="text-rose-500">*</span>
              </label>
              <input
                type="email"
                required
                placeholder="jane@company.com"
                value={formData.email}
                onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                className="w-full px-3 py-2 rounded-xl border border-slate-200 focus:ring-2 focus:ring-rose-500/20 focus:border-rose-500 text-xs"
              />
            </div>

            <div>
              <label className="block font-semibold uppercase text-slate-700 mb-1">Department</label>
              <input
                type="text"
                placeholder="e.g. Engineering"
                value={formData.department || ''}
                onChange={(e) => setFormData({ ...formData, department: e.target.value })}
                className="w-full px-3 py-2 rounded-xl border border-slate-200 focus:ring-2 focus:ring-rose-500/20 focus:border-rose-500 text-xs"
              />
            </div>

            <div>
              <label className="block font-semibold uppercase text-slate-700 mb-1">Photo URL</label>
              <input
                type="url"
                placeholder="https://example.com/avatar.jpg"
                value={formData.photo_url || ''}
                onChange={(e) => setFormData({ ...formData, photo_url: e.target.value })}
                className="w-full px-3 py-2 rounded-xl border border-slate-200 focus:ring-2 focus:ring-rose-500/20 focus:border-rose-500 text-xs"
              />
            </div>

            <div>
              <label className="block font-semibold uppercase text-slate-700 mb-1">Date of Birth</label>
              <input
                type="date"
                value={formData.date_of_birth || ''}
                onChange={(e) => setFormData({ ...formData, date_of_birth: e.target.value })}
                className="w-full px-3 py-2 rounded-xl border border-slate-200 focus:ring-2 focus:ring-rose-500/20 focus:border-rose-500 text-xs"
              />
            </div>

            <div>
              <label className="block font-semibold uppercase text-slate-700 mb-1">Date of Joining</label>
              <input
                type="date"
                value={formData.date_of_joining || ''}
                onChange={(e) => setFormData({ ...formData, date_of_joining: e.target.value })}
                className="w-full px-3 py-2 rounded-xl border border-slate-200 focus:ring-2 focus:ring-rose-500/20 focus:border-rose-500 text-xs"
              />
            </div>

            <div>
              <label className="block font-semibold uppercase text-slate-700 mb-1">
                Birthday Email Template
              </label>
              <select
                value={formData.birthday_template_id || ''}
                onChange={(e) =>
                  setFormData({
                    ...formData,
                    birthday_template_id: e.target.value ? e.target.value : null,
                  })
                }
                className="w-full px-3 py-2 rounded-xl border border-slate-200 bg-white focus:ring-2 focus:ring-rose-500/20 focus:border-rose-500 text-xs"
              >
                <option value="">(Use Organization Default Template)</option>
                {availableTemplates
                  .filter((t) => t.event_type === 'birthday' && t.is_active)
                  .map((t) => (
                    <option key={t.id} value={t.id}>
                      {t.name || t.variant_key} {t.is_default ? '⭐ (Default)' : ''}
                    </option>
                  ))}
              </select>
            </div>

            <div>
              <label className="block font-semibold uppercase text-slate-700 mb-1">
                Anniversary Email Template
              </label>
              <select
                value={formData.anniversary_template_id || ''}
                onChange={(e) =>
                  setFormData({
                    ...formData,
                    anniversary_template_id: e.target.value ? e.target.value : null,
                  })
                }
                className="w-full px-3 py-2 rounded-xl border border-slate-200 bg-white focus:ring-2 focus:ring-rose-500/20 focus:border-rose-500 text-xs"
              >
                <option value="">(Use Organization Default Template)</option>
                {availableTemplates
                  .filter((t) => t.event_type === 'work_anniversary' && t.is_active)
                  .map((t) => (
                    <option key={t.id} value={t.id}>
                      {t.name || t.variant_key} {t.is_default ? '⭐ (Default)' : ''}
                    </option>
                  ))}
              </select>
            </div>
          </div>

          <div className="flex items-center gap-2 pt-2">
            <input
              type="checkbox"
              id="create_is_active"
              checked={formData.is_active}
              onChange={(e) => setFormData({ ...formData, is_active: e.target.checked })}
              className="rounded border-slate-300 text-rose-600 focus:ring-rose-500"
            />
            <label htmlFor="create_is_active" className="text-xs text-slate-700 font-medium">
              Employee is currently Active (included in automated scans)
            </label>
          </div>

          <div className="flex items-center justify-end gap-3 pt-4 border-t border-slate-100">
            <button
              type="button"
              onClick={() => setIsCreateModalOpen(false)}
              className="px-4 py-2 rounded-xl text-xs font-semibold text-slate-600 hover:bg-slate-100"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={formSubmitting}
              className="px-5 py-2 rounded-xl bg-slate-900 hover:bg-slate-800 text-white text-xs font-semibold shadow-sm transition-all disabled:opacity-50"
            >
              {formSubmitting ? 'Saving...' : 'Save Employee'}
            </button>
          </div>
        </form>
      </Modal>

      {/* Edit Employee Modal */}
      <Modal
        isOpen={isEditModalOpen}
        onClose={() => setIsEditModalOpen(false)}
        title="Edit Employee Profile"
        subtitle={editingEmployee ? `Editing ${editingEmployee.full_name}` : ''}
        maxWidth="2xl"
      >
        <form onSubmit={handleEditSubmit} className="space-y-4">
          {formError && (
            <div className="p-3 rounded-xl bg-rose-50 border border-rose-200 text-xs text-rose-800">
              {formError}
            </div>
          )}

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-xs">
            <div>
              <label className="block font-semibold uppercase text-slate-700 mb-1">
                Employee Code <span className="text-rose-500">*</span>
              </label>
              <input
                type="text"
                required
                value={formData.employee_code}
                onChange={(e) => setFormData({ ...formData, employee_code: e.target.value })}
                className="w-full px-3 py-2 rounded-xl border border-slate-200 focus:ring-2 focus:ring-rose-500/20 focus:border-rose-500 text-xs"
              />
            </div>

            <div>
              <label className="block font-semibold uppercase text-slate-700 mb-1">
                Full Name <span className="text-rose-500">*</span>
              </label>
              <input
                type="text"
                required
                value={formData.full_name}
                onChange={(e) => setFormData({ ...formData, full_name: e.target.value })}
                className="w-full px-3 py-2 rounded-xl border border-slate-200 focus:ring-2 focus:ring-rose-500/20 focus:border-rose-500 text-xs"
              />
            </div>

            <div>
              <label className="block font-semibold uppercase text-slate-700 mb-1">Preferred Name</label>
              <input
                type="text"
                value={formData.preferred_name || ''}
                onChange={(e) => setFormData({ ...formData, preferred_name: e.target.value })}
                className="w-full px-3 py-2 rounded-xl border border-slate-200 focus:ring-2 focus:ring-rose-500/20 focus:border-rose-500 text-xs"
              />
            </div>

            <div>
              <label className="block font-semibold uppercase text-slate-700 mb-1">
                Email Address <span className="text-rose-500">*</span>
              </label>
              <input
                type="email"
                required
                value={formData.email}
                onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                className="w-full px-3 py-2 rounded-xl border border-slate-200 focus:ring-2 focus:ring-rose-500/20 focus:border-rose-500 text-xs"
              />
            </div>

            <div>
              <label className="block font-semibold uppercase text-slate-700 mb-1">Department</label>
              <input
                type="text"
                value={formData.department || ''}
                onChange={(e) => setFormData({ ...formData, department: e.target.value })}
                className="w-full px-3 py-2 rounded-xl border border-slate-200 focus:ring-2 focus:ring-rose-500/20 focus:border-rose-500 text-xs"
              />
            </div>

            <div>
              <label className="block font-semibold uppercase text-slate-700 mb-1">Photo URL</label>
              <input
                type="url"
                value={formData.photo_url || ''}
                onChange={(e) => setFormData({ ...formData, photo_url: e.target.value })}
                className="w-full px-3 py-2 rounded-xl border border-slate-200 focus:ring-2 focus:ring-rose-500/20 focus:border-rose-500 text-xs"
              />
            </div>

            <div>
              <label className="block font-semibold uppercase text-slate-700 mb-1">Date of Birth</label>
              <input
                type="date"
                value={formData.date_of_birth || ''}
                onChange={(e) => setFormData({ ...formData, date_of_birth: e.target.value })}
                className="w-full px-3 py-2 rounded-xl border border-slate-200 focus:ring-2 focus:ring-rose-500/20 focus:border-rose-500 text-xs"
              />
            </div>

            <div>
              <label className="block font-semibold uppercase text-slate-700 mb-1">Date of Joining</label>
              <input
                type="date"
                value={formData.date_of_joining || ''}
                onChange={(e) => setFormData({ ...formData, date_of_joining: e.target.value })}
                className="w-full px-3 py-2 rounded-xl border border-slate-200 focus:ring-2 focus:ring-rose-500/20 focus:border-rose-500 text-xs"
              />
            </div>

            <div>
              <label className="block font-semibold uppercase text-slate-700 mb-1">
                Birthday Email Template
              </label>
              <select
                value={formData.birthday_template_id || ''}
                onChange={(e) =>
                  setFormData({
                    ...formData,
                    birthday_template_id: e.target.value ? e.target.value : null,
                  })
                }
                className="w-full px-3 py-2 rounded-xl border border-slate-200 bg-white focus:ring-2 focus:ring-rose-500/20 focus:border-rose-500 text-xs"
              >
                <option value="">(Use Organization Default Template)</option>
                {availableTemplates
                  .filter((t) => t.event_type === 'birthday' && t.is_active)
                  .map((t) => (
                    <option key={t.id} value={t.id}>
                      {t.name || t.variant_key} {t.is_default ? '⭐ (Default)' : ''}
                    </option>
                  ))}
              </select>
            </div>

            <div>
              <label className="block font-semibold uppercase text-slate-700 mb-1">
                Anniversary Email Template
              </label>
              <select
                value={formData.anniversary_template_id || ''}
                onChange={(e) =>
                  setFormData({
                    ...formData,
                    anniversary_template_id: e.target.value ? e.target.value : null,
                  })
                }
                className="w-full px-3 py-2 rounded-xl border border-slate-200 bg-white focus:ring-2 focus:ring-rose-500/20 focus:border-rose-500 text-xs"
              >
                <option value="">(Use Organization Default Template)</option>
                {availableTemplates
                  .filter((t) => t.event_type === 'work_anniversary' && t.is_active)
                  .map((t) => (
                    <option key={t.id} value={t.id}>
                      {t.name || t.variant_key} {t.is_default ? '⭐ (Default)' : ''}
                    </option>
                  ))}
              </select>
            </div>
          </div>

          <div className="flex items-center gap-2 pt-2">
            <input
              type="checkbox"
              id="edit_is_active"
              checked={formData.is_active}
              onChange={(e) => setFormData({ ...formData, is_active: e.target.checked })}
              className="rounded border-slate-300 text-rose-600 focus:ring-rose-500"
            />
            <label htmlFor="edit_is_active" className="text-xs text-slate-700 font-medium">
              Employee is currently Active
            </label>
          </div>

          <div className="flex items-center justify-end gap-3 pt-4 border-t border-slate-100">
            <button
              type="button"
              onClick={() => setIsEditModalOpen(false)}
              className="px-4 py-2 rounded-xl text-xs font-semibold text-slate-600 hover:bg-slate-100"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={formSubmitting}
              className="px-5 py-2 rounded-xl bg-slate-900 hover:bg-slate-800 text-white text-xs font-semibold shadow-sm transition-all disabled:opacity-50"
            >
              {formSubmitting ? 'Saving...' : 'Update Employee'}
            </button>
          </div>
        </form>
      </Modal>

      {/* CSV Bulk Import Modal */}
      <CsvImportModal
        isOpen={isCsvModalOpen}
        onClose={() => setIsCsvModalOpen(false)}
        onSuccess={fetchEmployees}
      />
    </div>
  );
};
