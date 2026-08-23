import React, { useState } from 'react';

interface AvatarProps {
  name: string;
  photoUrl?: string | null;
  size?: 'sm' | 'md' | 'lg' | 'xl';
  className?: string;
}

export const Avatar: React.FC<AvatarProps> = ({ name, photoUrl, size = 'md', className = '' }) => {
  const [imageError, setImageError] = useState(false);

  const getInitials = (str: string): string => {
    if (!str) return '?';
    const parts = str.trim().split(/\s+/);
    if (parts.length === 1) return parts[0].substring(0, 2).toUpperCase();
    return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase();
  };

  const getBackgroundColor = (str: string): string => {
    const colors = [
      'bg-blue-100 text-blue-700 border-blue-200',
      'bg-indigo-100 text-indigo-700 border-indigo-200',
      'bg-purple-100 text-purple-700 border-purple-200',
      'bg-pink-100 text-pink-700 border-pink-200',
      'bg-rose-100 text-rose-700 border-rose-200',
      'bg-amber-100 text-amber-700 border-amber-200',
      'bg-emerald-100 text-emerald-700 border-emerald-200',
      'bg-teal-100 text-teal-700 border-teal-200',
    ];
    let hash = 0;
    for (let i = 0; i < str.length; i++) {
      hash = str.charCodeAt(i) + ((hash << 5) - hash);
    }
    const index = Math.abs(hash) % colors.length;
    return colors[index];
  };

  const sizeClasses = {
    sm: 'w-7 h-7 text-xs',
    md: 'w-9 h-9 text-sm',
    lg: 'w-12 h-12 text-base',
    xl: 'w-16 h-16 text-xl',
  }[size];

  if (photoUrl && !imageError) {
    return (
      <img
        src={photoUrl}
        alt={name}
        onError={() => setImageError(true)}
        className={`rounded-full object-cover border border-slate-200 shrink-0 ${sizeClasses} ${className}`}
      />
    );
  }

  return (
    <div
      className={`rounded-full flex items-center justify-center font-semibold border shrink-0 select-none ${getBackgroundColor(
        name
      )} ${sizeClasses} ${className}`}
    >
      {getInitials(name)}
    </div>
  );
};
