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
  event_type: EventType;
  variant_key: string;
  subject_line: string;
  html_body: string;
  is_active: boolean;
  created_at: string;
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

export type int = number;
