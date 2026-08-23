import React from 'react';
import { ChevronLeft, ChevronRight } from 'lucide-react';

interface PaginationProps {
  total: number;
  limit: number;
  offset: number;
  onPageChange: (newOffset: number) => void;
  onLimitChange?: (newLimit: number) => void;
}

export const Pagination: React.FC<PaginationProps> = ({
  total,
  limit,
  offset,
  onPageChange,
  onLimitChange,
}) => {
  const currentPage = Math.floor(offset / limit) + 1;
  const totalPages = Math.max(1, Math.ceil(total / limit));
  const startItem = total === 0 ? 0 : offset + 1;
  const endItem = Math.min(offset + limit, total);

  return (
    <div className="flex flex-col sm:flex-row items-center justify-between gap-4 px-4 py-3 border-t border-slate-100 bg-slate-50/50 text-xs text-slate-600">
      <div className="flex items-center gap-2">
        <span>
          Showing <span className="font-medium text-slate-900">{startItem}</span> to{' '}
          <span className="font-medium text-slate-900">{endItem}</span> of{' '}
          <span className="font-medium text-slate-900">{total}</span> items
        </span>
        {onLimitChange && (
          <div className="flex items-center gap-1.5 ml-4 pl-4 border-l border-slate-200">
            <span>Per page:</span>
            <select
              value={limit}
              onChange={(e) => onLimitChange(Number(e.target.value))}
              className="bg-white border border-slate-200 rounded-lg px-2 py-1 text-xs text-slate-700 focus:outline-none focus:ring-1 focus:ring-slate-400 cursor-pointer"
            >
              <option value={10}>10</option>
              <option value={25}>25</option>
              <option value={50}>50</option>
              <option value={100}>100</option>
            </select>
          </div>
        )}
      </div>

      <div className="flex items-center gap-1">
        <button
          type="button"
          onClick={() => onPageChange(Math.max(0, offset - limit))}
          disabled={currentPage <= 1}
          className="p-1.5 rounded-lg border border-slate-200 bg-white text-slate-600 hover:bg-slate-50 hover:text-slate-900 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
          title="Previous Page"
        >
          <ChevronLeft className="w-4 h-4" />
        </button>

        <div className="px-3 py-1 text-xs font-medium text-slate-700 bg-white border border-slate-200 rounded-lg">
          Page {currentPage} of {totalPages}
        </div>

        <button
          type="button"
          onClick={() => onPageChange(offset + limit)}
          disabled={currentPage >= totalPages}
          className="p-1.5 rounded-lg border border-slate-200 bg-white text-slate-600 hover:bg-slate-50 hover:text-slate-900 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
          title="Next Page"
        >
          <ChevronRight className="w-4 h-4" />
        </button>
      </div>
    </div>
  );
};
