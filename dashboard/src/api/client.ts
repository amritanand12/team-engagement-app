import {
  DigestLog,
  Employee,
  EmployeeCreatePayload,
  EmployeeDetail,
  EmployeeUpdatePayload,
  EventLog,
  EventTemplate,
  HrmsSyncResponse,
  PaginatedDigests,
  PaginatedEmployees,
  ResendResponse,
  ScanTriggerResponse,
  StatsSummary,
} from '../types';

const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';
const API_KEY_STORAGE_KEY = 'x-api-key';

export const getStoredApiKey = (): string | null => {
  return sessionStorage.getItem(API_KEY_STORAGE_KEY);
};

export const setStoredApiKey = (key: string): void => {
  sessionStorage.setItem(API_KEY_STORAGE_KEY, key.trim());
};

export const clearStoredApiKey = (): void => {
  sessionStorage.removeItem(API_KEY_STORAGE_KEY);
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
  const apiKey = getStoredApiKey();
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(options.headers as Record<string, string> || {}),
  };

  if (apiKey) {
    headers['x-api-key'] = apiKey;
  }

  const url = `${API_BASE}${endpoint}`;

  try {
    const response = await fetch(url, {
      ...options,
      headers,
    });

    if (response.status === 401) {
      clearStoredApiKey();
      if (onUnauthorizedCallback) {
        onUnauthorizedCallback('Invalid or expired admin API key. Please log in again.');
      }
      throw new ApiError('Invalid admin API key', 401);
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

  getTemplates: async (): Promise<EventTemplate[]> => {
    return apiFetch<EventTemplate[]>('/admin/templates');
  },

  updateTemplate: async (templateId: string, isActive: boolean): Promise<EventTemplate> => {
    return apiFetch<EventTemplate>(`/admin/templates/${templateId}`, {
      method: 'PATCH',
      body: JSON.stringify({ is_active: isActive }),
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
};
