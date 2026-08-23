import React, { useEffect, useState } from 'react';
import { api } from '../api/client';
import { StatsSummary } from '../types';
import { Badge } from '../components/common/Badge';
import { Avatar } from '../components/common/Avatar';
import { CardSkeleton, Skeleton } from '../components/common/Skeleton';
import {
  Users,
  Send,
  AlertTriangle,
  Calendar,
  ArrowUpRight,
  Sparkles,
  TrendingUp,
  RefreshCw,
  AlertCircle,
} from 'lucide-react';
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  Legend,
  CartesianGrid,
} from 'recharts';

interface OverviewPageProps {
  onNavigateTab: (tab: 'events' | 'employees' | 'digests' | 'templates') => void;
  onOpenScanModal: () => void;
}

export const OverviewPage: React.FC<OverviewPageProps> = ({ onNavigateTab, onOpenScanModal }) => {
  const [stats, setStats] = useState<StatsSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [chartRangeDays, setChartRangeDays] = useState<number>(30);

  const fetchStats = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.getStatsSummary(chartRangeDays);
      setStats(data);
    } catch (err: any) {
      setError(err.message || 'Failed to load dashboard statistics');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchStats();
  }, [chartRangeDays]);

  if (loading && !stats) {
    return (
      <div className="space-y-6">
        <CardSkeleton count={4} />
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="lg:col-span-2 p-6 rounded-2xl bg-white border border-slate-100 shadow-sm space-y-4">
            <Skeleton className="h-6 w-48" />
            <Skeleton className="h-64 w-full" />
          </div>
          <div className="p-6 rounded-2xl bg-white border border-slate-100 shadow-sm space-y-4">
            <Skeleton className="h-6 w-36" />
            <Skeleton className="h-64 w-full" />
          </div>
        </div>
      </div>
    );
  }

  if (error && !stats) {
    return (
      <div className="p-8 rounded-2xl bg-rose-50 border border-rose-200 text-rose-900 flex flex-col items-center justify-center text-center space-y-3">
        <AlertCircle className="w-10 h-10 text-rose-500" />
        <h3 className="text-base font-semibold">Unable to Load Overview</h3>
        <p className="text-xs text-rose-700 max-w-md">{error}</p>
        <button
          type="button"
          onClick={fetchStats}
          className="inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-rose-600 hover:bg-rose-700 text-white text-xs font-semibold shadow-sm transition-colors"
        >
          <RefreshCw className="w-3.5 h-3.5" />
          <span>Retry Loading</span>
        </button>
      </div>
    );
  }

  // Format daily stats for Recharts
  const chartData = (stats?.daily_stats || []).map((item) => ({
    name: item.date.substring(5), // 'MM-DD'
    Sent: item.sent,
    Failed: item.failed,
  }));

  return (
    <div className="space-y-8">
      {/* Top Banner / Hero */}
      <div className="relative overflow-hidden rounded-3xl bg-gradient-to-r from-slate-900 via-slate-800 to-rose-950 p-6 sm:p-8 text-white shadow-xl">
        <div className="relative z-10 flex flex-col md:flex-row items-start md:items-center justify-between gap-6">
          <div className="space-y-2 max-w-xl">
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-rose-500/20 border border-rose-500/30 text-rose-300 text-xs font-medium backdrop-blur-xs">
              <Sparkles className="w-3.5 h-3.5" />
              <span>Predictable & Automated Notifications</span>
            </div>
            <h1 className="text-xl sm:text-2xl font-extrabold tracking-tight">
              Team Engagement Operations
            </h1>
            <p className="text-xs sm:text-sm text-slate-300 leading-relaxed">
              Automating birthdays & milestone celebrations with static Jinja2 email templates and zero
              runtime LLM hallucination risk.
            </p>
          </div>

          <div className="flex items-center gap-3">
            <button
              type="button"
              onClick={onOpenScanModal}
              className="inline-flex items-center gap-2 px-5 py-2.5 rounded-2xl bg-rose-600 hover:bg-rose-500 text-white font-semibold text-xs sm:text-sm shadow-lg shadow-rose-600/30 transition-all hover:scale-102 active:scale-98"
            >
              <span>Trigger Scan Now</span>
              <ArrowUpRight className="w-4 h-4" />
            </button>
          </div>
        </div>
      </div>

      {/* KPI Cards Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 sm:gap-6">
        {/* Total Employees */}
        <div
          onClick={() => onNavigateTab('employees')}
          className="group cursor-pointer p-5 rounded-2xl bg-white border border-slate-100 shadow-sm hover:shadow-md hover:border-slate-200 transition-all"
        >
          <div className="flex items-center justify-between text-slate-500 mb-3">
            <span className="text-xs font-semibold uppercase tracking-wider">Total Staff</span>
            <div className="w-9 h-9 rounded-xl bg-blue-50 text-blue-600 flex items-center justify-center group-hover:scale-110 transition-transform">
              <Users className="w-4 h-4" />
            </div>
          </div>
          <div className="text-2xl sm:text-3xl font-extrabold text-slate-800">
            {stats?.total_employees ?? 0}
          </div>
          <div className="flex items-center gap-2 mt-2 text-xs text-slate-500">
            <span className="inline-flex items-center text-emerald-600 font-semibold">
              {stats?.active_employees ?? 0} active
            </span>
            <span>·</span>
            <span>{stats?.inactive_employees ?? 0} inactive</span>
          </div>
        </div>

        {/* Sent Today */}
        <div
          onClick={() => onNavigateTab('events')}
          className="group cursor-pointer p-5 rounded-2xl bg-white border border-slate-100 shadow-sm hover:shadow-md hover:border-slate-200 transition-all"
        >
          <div className="flex items-center justify-between text-slate-500 mb-3">
            <span className="text-xs font-semibold uppercase tracking-wider">Sent Today</span>
            <div className="w-9 h-9 rounded-xl bg-emerald-50 text-emerald-600 flex items-center justify-center group-hover:scale-110 transition-transform">
              <Send className="w-4 h-4" />
            </div>
          </div>
          <div className="text-2xl sm:text-3xl font-extrabold text-emerald-600">
            {stats?.today_stats.sent ?? 0}
          </div>
          <div className="mt-2 text-xs text-slate-500">
            Individual celebration emails delivered today
          </div>
        </div>

        {/* Failed Today */}
        <div
          onClick={() => onNavigateTab('events')}
          className="group cursor-pointer p-5 rounded-2xl bg-white border border-slate-100 shadow-sm hover:shadow-md hover:border-slate-200 transition-all"
        >
          <div className="flex items-center justify-between text-slate-500 mb-3">
            <span className="text-xs font-semibold uppercase tracking-wider">Failed Today</span>
            <div className={`w-9 h-9 rounded-xl flex items-center justify-center group-hover:scale-110 transition-transform ${
              (stats?.today_stats.failed ?? 0) > 0
                ? 'bg-rose-100 text-rose-600'
                : 'bg-slate-100 text-slate-400'
            }`}>
              <AlertTriangle className="w-4 h-4" />
            </div>
          </div>
          <div className={`text-2xl sm:text-3xl font-extrabold ${
            (stats?.today_stats.failed ?? 0) > 0 ? 'text-rose-600' : 'text-slate-800'
          }`}>
            {stats?.today_stats.failed ?? 0}
          </div>
          <div className="mt-2 text-xs text-slate-500">
            {(stats?.today_stats.failed ?? 0) > 0 ? 'Requires attention / retry' : 'All systems operating smoothly'}
          </div>
        </div>

        {/* Upcoming 7 Days */}
        <div className="p-5 rounded-2xl bg-white border border-slate-100 shadow-sm">
          <div className="flex items-center justify-between text-slate-500 mb-3">
            <span className="text-xs font-semibold uppercase tracking-wider">Upcoming (7 Days)</span>
            <div className="w-9 h-9 rounded-xl bg-purple-50 text-purple-600 flex items-center justify-center">
              <Calendar className="w-4 h-4" />
            </div>
          </div>
          <div className="text-2xl sm:text-3xl font-extrabold text-purple-600">
            {stats?.upcoming_events_7d.length ?? 0}
          </div>
          <div className="mt-2 text-xs text-slate-500">
            Due celebrations over next 7 days
          </div>
        </div>
      </div>

      {/* Main Charts & Side Section */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Chart (2 Cols) */}
        <div className="lg:col-span-2 p-6 rounded-3xl bg-white border border-slate-100 shadow-sm space-y-4">
          <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
            <div>
              <h3 className="text-base font-bold text-slate-800 flex items-center gap-2">
                <TrendingUp className="w-4 h-4 text-slate-500" />
                <span>Delivery Activity Trend</span>
              </h3>
              <p className="text-xs text-slate-500 mt-0.5">
                Sent vs Failed email notifications over the selected time range
              </p>
            </div>

            <div className="flex items-center gap-1 bg-slate-100 p-1 rounded-xl text-xs font-medium text-slate-600">
              {[7, 14, 30].map((days) => (
                <button
                  key={days}
                  type="button"
                  onClick={() => setChartRangeDays(days)}
                  className={`px-3 py-1 rounded-lg transition-colors ${
                    chartRangeDays === days
                      ? 'bg-white text-slate-900 shadow-xs font-semibold'
                      : 'hover:text-slate-900'
                  }`}
                >
                  {days} Days
                </button>
              ))}
            </div>
          </div>

          <div className="h-72 w-full pt-4">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={chartData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" vertical={false} />
                <XAxis dataKey="name" stroke="#94a3b8" fontSize={11} tickLine={false} />
                <YAxis stroke="#94a3b8" fontSize={11} tickLine={false} allowDecimals={false} />
                <Tooltip
                  contentStyle={{
                    backgroundColor: '#0f172a',
                    borderRadius: '12px',
                    border: 'none',
                    color: '#fff',
                    fontSize: '12px',
                    boxShadow: '0 10px 15px -3px rgba(0, 0, 0, 0.1)',
                  }}
                />
                <Legend iconType="circle" wrapperStyle={{ fontSize: '12px', paddingTop: '8px' }} />
                <Bar dataKey="Sent" fill="#10b981" radius={[4, 4, 0, 0]} maxBarSize={28} />
                <Bar dataKey="Failed" fill="#f43f5e" radius={[4, 4, 0, 0]} maxBarSize={28} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Upcoming Celebrations (1 Col) */}
        <div className="p-6 rounded-3xl bg-white border border-slate-100 shadow-sm flex flex-col">
          <div className="flex items-center justify-between pb-4 border-b border-slate-100">
            <div>
              <h3 className="text-base font-bold text-slate-800">Next 7 Days</h3>
              <p className="text-xs text-slate-500 mt-0.5">Upcoming scheduled celebrations</p>
            </div>
            <button
              type="button"
              onClick={fetchStats}
              className="p-1.5 rounded-lg text-slate-400 hover:text-slate-600 hover:bg-slate-50 transition-colors"
              title="Refresh Stats"
            >
              <RefreshCw className="w-3.5 h-3.5" />
            </button>
          </div>

          <div className="flex-1 overflow-y-auto divide-y divide-slate-50 max-h-[320px] pr-1 mt-2">
            {(stats?.upcoming_events_7d || []).length === 0 ? (
              <div className="py-12 text-center text-slate-400 text-xs">
                No celebrations falling in the next 7 days.
              </div>
            ) : (
              (stats?.upcoming_events_7d || []).map((ev, idx) => (
                <div key={idx} className="py-3 flex items-center justify-between gap-3">
                  <div className="flex items-center gap-3 min-w-0">
                    <Avatar name={ev.employee_name} photoUrl={ev.photo_url} size="md" />
                    <div className="min-w-0">
                      <div className="text-xs font-bold text-slate-800 truncate">
                        {ev.employee_name}
                      </div>
                      <div className="text-[11px] text-slate-500 truncate">
                        {ev.department || 'General'}
                      </div>
                    </div>
                  </div>

                  <div className="text-right shrink-0">
                    <Badge eventType={ev.event_type} size="sm" />
                    <div className="text-[10px] text-slate-400 font-mono mt-1">
                      {ev.event_date}
                      {ev.years ? ` (${ev.years}yr)` : ''}
                    </div>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
