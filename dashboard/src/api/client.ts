import {
  DigestLog,
  Employee,
  EmployeeCreatePayload,
  EmployeeDetail,
  EmployeeUpdatePayload,
  EventLog,
  EventTemplate,
  TemplateCreatePayload,
  TemplateUpdatePayload,
  TemplatePreviewResponse,
  EventType,
  HrmsSyncResponse,
  Organization,
  PaginatedDigests,
  PaginatedEmployees,
  ResendResponse,
  ScanTriggerResponse,
  StatsSummary,
  TestDbConnectionPayload,
  TestDbConnectionResponse,
  TestSmtpConnectionPayload,
  TestSmtpConnectionResponse,
  PhotoRequestResponse,
  PublicPhotoInfo,
} from '../types';

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? '';
const AUTH_TOKEN_KEY = 'auth-token';
const API_KEY_STORAGE_KEY = 'x-api-key';
const TENANT_ID_STORAGE_KEY = 'x-tenant-id';

export const getStoredAuthToken = (): string | null => {
  return sessionStorage.getItem(AUTH_TOKEN_KEY);
};

export const setStoredAuthToken = (token: string): void => {
  sessionStorage.setItem(AUTH_TOKEN_KEY, token.trim());
};

export const clearStoredAuthToken = (): void => {
  sessionStorage.removeItem(AUTH_TOKEN_KEY);
};

export const getStoredApiKey = (): string | null => {
  return sessionStorage.getItem(API_KEY_STORAGE_KEY);
};

export const setStoredApiKey = (key: string): void => {
  sessionStorage.setItem(API_KEY_STORAGE_KEY, key.trim());
};

export const clearStoredApiKey = (): void => {
  sessionStorage.removeItem(API_KEY_STORAGE_KEY);
};

export const getStoredTenantId = (): string | null => {
  return sessionStorage.getItem(TENANT_ID_STORAGE_KEY);
};

export const setStoredTenantId = (tenantId: string): void => {
  sessionStorage.setItem(TENANT_ID_STORAGE_KEY, tenantId.trim());
};

export const clearStoredTenantId = (): void => {
  sessionStorage.removeItem(TENANT_ID_STORAGE_KEY);
};

export class ApiError extends Error {
  status: number;
  data: any;

  constructor(message: string, status: number, data?: any) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.data = data;
  }
}

let onUnauthorizedCallback: ((message?: string) => void) | null = null;

export const setOnUnauthorizedCallback = (cb: (message?: string) => void) => {
  onUnauthorizedCallback = cb;
};

async function apiFetch<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
  const token = getStoredAuthToken();
  const apiKey = getStoredApiKey();
  const tenantId = getStoredTenantId();

  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(options.headers as Record<string, string> || {}),
  };

  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }
  if (apiKey) {
    headers['x-api-key'] = apiKey;
  }
  if (tenantId) {
    headers['x-tenant-id'] = tenantId;
  }

  const url = `${API_BASE}${endpoint}`;

  try {
    const response = await fetch(url, {
      ...options,
      headers,
    });

    // Only fire the global unauthorized callback for authenticated endpoints,
    // NOT for /auth/login itself (which legitimately returns 401 for wrong credentials).
    if (response.status === 401 && !endpoint.startsWith('/auth/login')) {
      clearStoredApiKey();
      if (onUnauthorizedCallback) {
        onUnauthorizedCallback('Session expired. Please log in again.');
      }
      throw new ApiError('Session expired. Please log in again.', 401);
    }

    if (!response.ok) {
      let errorDetail = `Request failed with status ${response.status}`;
      let data: any = null;
      try {
        data = await response.json();
        if (data && data.detail) {
          errorDetail = typeof data.detail === 'string' ? data.detail : JSON.stringify(data.detail);
        }
      } catch {
        // Ignore json parse error for non-json responses
      }
      throw new ApiError(errorDetail, response.status, data);
    }

    return (await response.json()) as T;
  } catch (error) {
    if (error instanceof ApiError) {
      throw error;
    }
    throw new ApiError(
      error instanceof Error ? error.message : 'Network error or backend unreachable',
      0
    );
  }
}

export const api = {
  health: async (): Promise<{ status: string }> => {
    return apiFetch<{ status: string }>('/health');
  },

  triggerScan: async (scanDate?: string): Promise<ScanTriggerResponse> => {
    const params = scanDate ? `?scan_date=${encodeURIComponent(scanDate)}` : '';
    return apiFetch<ScanTriggerResponse>(`/admin/scan/trigger${params}`, {
      method: 'POST',
    });
  },

  getStatsSummary: async (days: number = 30): Promise<StatsSummary> => {
    return apiFetch<StatsSummary>(`/admin/stats/summary?days=${days}`);
  },

  getEvents: async (params?: { batch_id?: string; status?: string; employee_id?: string }): Promise<EventLog[]> => {
    const query = new URLSearchParams();
    if (params?.batch_id) query.append('batch_id', params.batch_id);
    if (params?.status) query.append('status', params.status);
    if (params?.employee_id) query.append('employee_id', params.employee_id);
    const qs = query.toString();
    return apiFetch<EventLog[]>(`/admin/events${qs ? `?${qs}` : ''}`);
  },

  getEvent: async (eventId: string): Promise<EventLog> => {
    return apiFetch<EventLog>(`/admin/events/${eventId}`);
  },

  resendEvent: async (eventId: string): Promise<ResendResponse> => {
    return apiFetch<ResendResponse>(`/admin/events/${eventId}/resend`, {
      method: 'POST',
    });
  },

  getEmployees: async (params?: {
    search?: string;
    is_active?: boolean;
    limit?: number;
    offset?: number;
  }): Promise<PaginatedEmployees> => {
    const query = new URLSearchParams();
    if (params?.search) query.append('search', params.search);
    if (params?.is_active !== undefined) query.append('is_active', String(params.is_active));
    if (params?.limit !== undefined) query.append('limit', String(params.limit));
    if (params?.offset !== undefined) query.append('offset', String(params.offset));
    const qs = query.toString();
    return apiFetch<PaginatedEmployees>(`/admin/employees${qs ? `?${qs}` : ''}`);
  },

  getEmployee: async (employeeId: string): Promise<EmployeeDetail> => {
    return apiFetch<EmployeeDetail>(`/admin/employees/${employeeId}`);
  },

  createEmployee: async (payload: EmployeeCreatePayload): Promise<Employee> => {
    return apiFetch<Employee>('/admin/employees', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  },

  updateEmployee: async (employeeId: string, payload: EmployeeUpdatePayload): Promise<Employee> => {
    return apiFetch<Employee>(`/admin/employees/${employeeId}`, {
      method: 'PATCH',
      body: JSON.stringify(payload),
    });
  },

  requestEmployeePhoto: async (employeeId: string): Promise<PhotoRequestResponse> => {
    return apiFetch<PhotoRequestResponse>(`/admin/employees/${employeeId}/request-photo`, {
      method: 'POST',
    });
  },

  uploadEmployeePhoto: async (employeeId: string, file: File): Promise<Employee> => {
    const formData = new FormData();
    formData.append('file', file);
    const token = getStoredAuthToken();
    const apiKey = getStoredApiKey();
    const headers: Record<string, string> = {};
    if (token) headers['Authorization'] = `Bearer ${token}`;
    if (apiKey) headers['x-api-key'] = apiKey;

    const response = await fetch(`${API_BASE}/admin/employees/${employeeId}/upload-photo`, {
      method: 'POST',
      headers,
      body: formData,
    });
    if (!response.ok) {
      let errDetail = 'Photo upload failed';
      try {
        const d = await response.json();
        if (d?.detail) errDetail = typeof d.detail === 'string' ? d.detail : JSON.stringify(d.detail);
      } catch {}
      throw new ApiError(errDetail, response.status);
    }
    return await response.json();
  },

  scanPhotoRequests: async (scanDate?: string): Promise<any[]> => {
    const params = scanDate ? `?scan_date=${encodeURIComponent(scanDate)}` : '';
    return apiFetch<any[]>(`/admin/photo-requests/scan${params}`, {
      method: 'POST',
    });
  },

  getPublicPhotoInfo: async (token: string): Promise<PublicPhotoInfo> => {
    const res = await fetch(`${API_BASE}/api/public/photo-info?token=${encodeURIComponent(token)}`);
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || 'Failed to load photo request info');
    }
    return res.json();
  },

  uploadPublicPhoto: async (token: string, file: File): Promise<any> => {
    const formData = new FormData();
    formData.append('token', token);
    formData.append('file', file);
    const res = await fetch(`${API_BASE}/api/public/upload-photo`, {
      method: 'POST',
      body: formData,
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || 'Failed to upload photo');
    }
    return res.json();
  },

  getTemplates: async (): Promise<EventTemplate[]> => {
    return apiFetch<EventTemplate[]>('/admin/templates');
  },

  createTemplate: async (payload: TemplateCreatePayload): Promise<EventTemplate> => {
    return apiFetch<EventTemplate>('/admin/templates', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  },

  updateTemplate: async (templateId: string, payload: TemplateUpdatePayload): Promise<EventTemplate> => {
    return apiFetch<EventTemplate>(`/admin/templates/${templateId}`, {
      method: 'PATCH',
      body: JSON.stringify(payload),
    });
  },

  deleteTemplate: async (templateId: string): Promise<{ message: string; template_id: string }> => {
    return apiFetch<{ message: string; template_id: string }>(`/admin/templates/${templateId}`, {
      method: 'DELETE',
    });
  },

  previewTemplate: async (payload: {
    subject_line: string;
    html_body: string;
    event_type: EventType;
  }): Promise<TemplatePreviewResponse> => {
    return apiFetch<TemplatePreviewResponse>('/admin/templates/preview', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  },

  getDigests: async (params?: { limit?: number; offset?: number }): Promise<PaginatedDigests> => {
    const query = new URLSearchParams();
    if (params?.limit !== undefined) query.append('limit', String(params.limit));
    if (params?.offset !== undefined) query.append('offset', String(params.offset));
    const qs = query.toString();
    return apiFetch<PaginatedDigests>(`/admin/digests${qs ? `?${qs}` : ''}`);
  },

  getDigest: async (batchId: string): Promise<DigestLog> => {
    return apiFetch<DigestLog>(`/admin/digests/${batchId}`);
  },

  triggerHrmsSync: async (): Promise<HrmsSyncResponse> => {
    return apiFetch<HrmsSyncResponse>('/admin/hrms-sync/trigger', {
      method: 'POST',
    });
  },

  getOrganization: async (): Promise<any> => {
    return apiFetch<any>('/admin/organization');
  },

  updateOrganization: async (payload: any): Promise<Organization> => {
    return apiFetch<Organization>('/admin/organization', {
      method: 'PATCH',
      body: JSON.stringify(payload),
    });
  },

  testDatabaseConnection: async (payload: TestDbConnectionPayload): Promise<TestDbConnectionResponse> => {
    return apiFetch<TestDbConnectionResponse>('/admin/settings/test-db', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  },

  saveDatabaseConfiguration: async (payload: TestDbConnectionPayload): Promise<Organization> => {
    return apiFetch<Organization>('/admin/settings/database', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  },

  testSmtpConnection: async (payload: TestSmtpConnectionPayload): Promise<TestSmtpConnectionResponse> => {
    return apiFetch<TestSmtpConnectionResponse>('/admin/settings/test-smtp', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  },

  saveSmtpConfiguration: async (payload: TestSmtpConnectionPayload): Promise<Organization> => {
    return apiFetch<Organization>('/admin/settings/smtp', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  },

  uploadEmployeesCsv: async (file: File): Promise<any> => {
    const apiKey = getStoredApiKey();
    const formData = new FormData();
    formData.append('file', file);

    const headers: Record<string, string> = {};
    if (apiKey) {
      headers['x-api-key'] = apiKey;
    }

    const response = await fetch(`${API_BASE}/admin/employees/upload-csv`, {
      method: 'POST',
      headers,
      body: formData,
    });

    if (!response.ok) {
      let errDetail = 'CSV upload failed';
      try {
        const d = await response.json();
        if (d?.detail) errDetail = typeof d.detail === 'string' ? d.detail : JSON.stringify(d.detail);
      } catch {}
      throw new ApiError(errDetail, response.status);
    }
    return await response.json();
  },

  resetDemo: async (): Promise<any> => {
    return apiFetch<any>('/admin/demo/reset', {
      method: 'POST',
    });
  },

  // Auth Methods
  loginWithEmail: async (email: string, password: string): Promise<any> => {
    return apiFetch<any>('/auth/login', {
      method: 'POST',
      body: JSON.stringify({ email, password }),
    });
  },

  loginWithApiKey: async (apiKey: string): Promise<any> => {
    return apiFetch<any>('/auth/api-key', {
      method: 'POST',
      body: JSON.stringify({ api_key: apiKey }),
    });
  },

  getCurrentProfile: async (): Promise<any> => {
    return apiFetch<any>('/auth/me');
  },

  // SuperAdmin Methods
  getSuperAdminOrganizations: async (): Promise<any[]> => {
    return apiFetch<any[]>('/superadmin/organizations');
  },

  createOrganization: async (payload: any): Promise<any> => {
    return apiFetch<any>('/superadmin/organizations', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  },

  toggleOrganizationStatus: async (orgId: string, isActive: boolean): Promise<any> => {
    return apiFetch<any>(`/superadmin/organizations/${orgId}/status?is_active=${isActive}`, {
      method: 'PATCH',
    });
  },

  changePassword: async (currentPassword: string, newPassword: string, confirmPassword: string): Promise<any> => {
    return apiFetch<any>('/auth/change-password', {
      method: 'POST',
      body: JSON.stringify({
        current_password: currentPassword,
        new_password: newPassword,
        confirm_password: confirmPassword,
      }),
    });
  },

  resetTenantPassword: async (orgId: string, newPassword: string): Promise<any> => {
    return apiFetch<any>(`/superadmin/organizations/${orgId}/reset-password`, {
      method: 'POST',
      body: JSON.stringify({
        new_password: newPassword,
      }),
    });
  },

  deleteOrganization: async (orgId: string): Promise<any> => {
    return apiFetch<any>(`/superadmin/organizations/${orgId}`, {
      method: 'DELETE',
    });
  },

  getAuditLogs: async (params?: { limit?: number; offset?: number; action?: string; search?: string }): Promise<any> => {
    const query = new URLSearchParams();
    if (params?.limit) query.append('limit', params.limit.toString());
    if (params?.offset !== undefined) query.append('offset', params.offset.toString());
    if (params?.action) query.append('action', params.action);
    if (params?.search) query.append('search', params.search);
    const qs = query.toString();
    return apiFetch<any>(`/superadmin/audit-logs${qs ? `?${qs}` : ''}`);
  },
};
