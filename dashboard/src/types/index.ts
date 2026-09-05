export type EventType = 'birthday' | 'work_anniversary';

export type EventStatus = 'pending' | 'rendered' | 'sent' | 'failed' | 'skipped';

export type DigestStatus = 'pending' | 'sent' | 'failed' | 'empty_skipped';

export interface Employee {
  id: string;
  employee_code: string;
  full_name: string;
  preferred_name: string | null;
  email: string;
  photo_url: string | null;
  date_of_birth: string | null;
  date_of_joining: string | null;
  department: string | null;
  manager_id: string | null;
  team_channel_id: string | null;
  is_active: boolean;
  birthday_template_id: string | null;
  anniversary_template_id: string | null;
  last_synced_at: string | null;
}

export interface EmployeeCreatePayload {
  employee_code: string;
  full_name: string;
  preferred_name?: string | null;
  email: string;
  photo_url?: string | null;
  date_of_birth?: string | null;
  date_of_joining?: string | null;
  department?: string | null;
  manager_id?: string | null;
  team_channel_id?: string | null;
  birthday_template_id?: string | null;
  anniversary_template_id?: string | null;
  is_active?: boolean;
}

export interface EmployeeUpdatePayload {
  employee_code?: string;
  full_name?: string;
  preferred_name?: string | null;
  email?: string;
  photo_url?: string | null;
  date_of_birth?: string | null;
  date_of_joining?: string | null;
  department?: string | null;
  manager_id?: string | null;
  team_channel_id?: string | null;
  birthday_template_id?: string | null;
  anniversary_template_id?: string | null;
  is_active?: boolean;
}

export interface PaginatedEmployees {
  items: Employee[];
  total: number;
  limit: number;
  offset: number;
}


export interface EventLog {
  id: string;
  employee_id: string;
  event_type: EventType;
  event_date: string;
  years: number | null;
  status: EventStatus;
  batch_id: string;
  attempt_count: number;
  error_detail: string | null;
  rendered_subject: string | null;
  rendered_html: string | null;
  sent_at: string | null;
  created_at: string;
  employee_name?: string | null;
}

export interface EmployeeDetail extends Employee {
  recent_events: EventLog[];
}

export interface EventTemplate {
  id: string;
  name?: string;
  event_type: EventType;
  variant_key: string;
  subject_line: string;
  html_body: string;
  is_active: boolean;
  is_default: boolean;
  created_at: string;
}

export interface TemplateCreatePayload {
  name: string;
  event_type: EventType;
  subject_line: string;
  html_body: string;
  variant_key?: string;
  is_default?: boolean;
  is_active?: boolean;
}

export interface TemplateUpdatePayload {
  name?: string;
  subject_line?: string;
  html_body?: string;
  is_default?: boolean;
  is_active?: boolean;
}

export interface TemplatePreviewResponse {
  rendered_subject: string;
  rendered_html: string;
}

export interface DailyStatsItem {
  date: string;
  batch_id: string;
  sent: number;
  failed: number;
  pending: number;
  skipped: number;
}

export interface UpcomingEventItem {
  employee_id: string;
  employee_name: string;
  preferred_name: string | null;
  photo_url: string | null;
  department: string | null;
  event_type: EventType;
  event_date: string;
  years: number | null;
}

export interface TodayStats {
  sent: number;
  failed: number;
  pending: number;
  skipped: number;
}

export interface StatsSummary {
  total_employees: number;
  active_employees: number;
  inactive_employees: number;
  today_stats: TodayStats;
  upcoming_events_7d: UpcomingEventItem[];
  daily_stats: DailyStatsItem[];
}

export interface DigestLog {
  id: string;
  batch_id: string;
  channel_id: string;
  status: DigestStatus;
  rendered_html: string | null;
  event_count: number;
  error_detail: string | null;
  sent_at: string | null;
  created_at: string;
}

export interface PaginatedDigests {
  items: DigestLog[];
  total: number;
  limit: number;
  offset: number;
}

export interface ScanTriggerResponse {
  batch_id: string;
  detected: number;
  rendered: number;
  sent: number;
  failed: number;
  skipped: number;
  digest_status: string;
}

export interface ResendResponse {
  event_id: string;
  status: EventStatus;
  message: string;
}

export interface HrmsSyncResponse {
  created: number;
  updated: number;
  message: string;
}

export interface Organization {
  id: string;
  name: string;
  slug: string;
  api_key: string;
  company_logo_url: string | null;
  business_timezone: string;
  leap_day_policy: string;
  digest_channel_id: string;
  smtp_host: string | null;
  smtp_port: number | null;
  smtp_username: string | null;
  smtp_from_address: string | null;
  slack_webhook_url: string | null;
  teams_webhook_url: string | null;
  is_active: boolean;
  is_demo: boolean;
  created_at: string;
}

export interface OrganizationUpdatePayload {
  name?: string;
  company_logo_url?: string | null;
  business_timezone?: string;
  leap_day_policy?: string;
  digest_channel_id?: string;
  smtp_host?: string | null;
  smtp_port?: number | null;
  smtp_username?: string | null;
  smtp_password?: string | null;
  smtp_from_address?: string | null;
  slack_webhook_url?: string | null;
  teams_webhook_url?: string | null;
}

export interface CsvImportError {
  row: number;
  error: string;
}

export interface CsvImportResponse {
  total_rows: number;
  imported: number;
  updated: number;
  failed: number;
  errors: CsvImportError[];
}

export interface DemoResetResponse {
  success: boolean;
  message: string;
  employee_count: number;
  events_detected: number;
}

export type UserRole = 'super_admin' | 'tenant_admin' | 'hr_manager' | 'viewer';

export interface User {
  id: string;
  email: string;
  full_name: string;
  role: UserRole;
  organization_id: string | null;
  is_active: boolean;
  created_at: string;
}

export interface AuthResponse {
  access_token: string;
  token_type: string;
  user: User;
  organization: Organization | null;
}

export interface SuperAdminOrg {
  id: string;
  name: string;
  slug: string;
  api_key: string;
  company_logo_url: string | null;
  business_timezone: string;
  is_active: boolean;
  is_demo: boolean;
  employee_count: number;
  event_count: number;
  created_at: string;
}

export interface CreateTenantPayload {
  name: string;
  slug?: string;
  admin_email: string;
  admin_name: string;
  admin_password: string;
  business_timezone?: string;
  leap_day_policy?: string;
}

export interface ChangePasswordPayload {
  current_password: str;
  new_password: str;
  confirm_password: str;
}

export interface ResetPasswordPayload {
  new_password: str;
}

export interface ChangePasswordResponse {
  success: boolean;
  message: string;
}

export type str = string;
export type int = number;
