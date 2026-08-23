import React from 'react';
import { DigestStatus, EventStatus, EventType } from '../../types';

interface BadgeProps {
  status?: EventStatus | DigestStatus | 'active' | 'inactive';
  eventType?: EventType;
  children?: React.ReactNode;
  size?: 'sm' | 'md';
}

export const Badge: React.FC<BadgeProps> = ({ status, eventType, children, size = 'sm' }) => {
  const sizeClasses = size === 'sm' ? 'px-2 py-0.5 text-xs' : 'px-2.5 py-1 text-xs';

  if (eventType) {
    if (eventType === 'birthday') {
      return (
        <span className={`inline-flex items-center gap-1 font-medium rounded-full bg-pink-50 text-pink-700 border border-pink-200/80 ${sizeClasses}`}>
          <span>🎂</span>
          <span>Birthday</span>
        </span>
      );
    }
    return (
      <span className={`inline-flex items-center gap-1 font-medium rounded-full bg-purple-50 text-purple-700 border border-purple-200/80 ${sizeClasses}`}>
        <span>🎉</span>
        <span>Anniversary</span>
      </span>
    );
  }

  const getStatusStyle = () => {
    switch (status) {
      case 'sent':
        return 'bg-emerald-50 text-emerald-700 border-emerald-200';
      case 'failed':
        return 'bg-rose-50 text-rose-700 border-rose-200';
      case 'pending':
        return 'bg-slate-100 text-slate-700 border-slate-200';
      case 'rendered':
        return 'bg-sky-50 text-sky-700 border-sky-200';
      case 'skipped':
      case 'empty_skipped':
        return 'bg-amber-50 text-amber-700 border-amber-200';
      case 'active':
        return 'bg-emerald-50 text-emerald-700 border-emerald-200';
      case 'inactive':
        return 'bg-slate-100 text-slate-500 border-slate-200';
      default:
        return 'bg-slate-100 text-slate-600 border-slate-200';
    }
  };

  const getStatusLabel = () => {
    switch (status) {
      case 'sent':
        return 'Sent';
      case 'failed':
        return 'Failed';
      case 'pending':
        return 'Pending';
      case 'rendered':
        return 'Rendered';
      case 'skipped':
        return 'Skipped';
      case 'empty_skipped':
        return 'Empty (Skipped)';
      case 'active':
        return 'Active';
      case 'inactive':
        return 'Inactive';
      default:
        return children || status;
    }
  };

  const getDotColor = () => {
    switch (status) {
      case 'sent':
      case 'active':
        return 'bg-emerald-500';
      case 'failed':
        return 'bg-rose-500';
      case 'rendered':
        return 'bg-sky-500';
      case 'skipped':
      case 'empty_skipped':
        return 'bg-amber-500';
      default:
        return 'bg-slate-400';
    }
  };

  return (
    <span className={`inline-flex items-center gap-1.5 font-medium rounded-full border ${getStatusStyle()} ${sizeClasses}`}>
      <span className={`w-1.5 h-1.5 rounded-full ${getDotColor()}`} />
      <span>{getStatusLabel()}</span>
    </span>
  );
};
