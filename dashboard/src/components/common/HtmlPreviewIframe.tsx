import React, { useState } from 'react';
import { Smartphone, Monitor, AlertCircle } from 'lucide-react';

interface HtmlPreviewIframeProps {
  htmlContent: string | null | undefined;
  title?: string;
  className?: string;
  minHeight?: string;
}

export const HtmlPreviewIframe: React.FC<HtmlPreviewIframeProps> = ({
  htmlContent,
  title = 'Email Preview',
  className = '',
  minHeight = '420px',
}) => {
  const [deviceMode, setDeviceMode] = useState<'desktop' | 'mobile'>('desktop');

  if (!htmlContent) {
    return (
      <div
        className={`flex flex-col items-center justify-center p-8 rounded-xl bg-slate-50 border border-dashed border-slate-200 text-slate-400 text-sm ${className}`}
        style={{ minHeight }}
      >
        <AlertCircle className="w-8 h-8 mb-2 text-slate-300" />
        <p className="font-medium text-slate-600">No rendered preview available</p>
        <p className="text-xs text-slate-400 mt-0.5">This event may not have been rendered yet or was skipped.</p>
      </div>
    );
  }

  return (
    <div className={`flex flex-col border border-slate-200 rounded-xl overflow-hidden bg-slate-100/70 shadow-inner ${className}`}>
      {/* Top Preview Controls */}
      <div className="flex items-center justify-between px-3 py-2 bg-slate-200/60 border-b border-slate-200 text-xs text-slate-600">
        <span className="font-medium truncate max-w-[240px] text-slate-700">{title}</span>
        <div className="flex items-center gap-1 bg-white/80 border border-slate-300/80 rounded-lg p-0.5 shadow-sm">
          <button
            type="button"
            onClick={() => setDeviceMode('desktop')}
            className={`flex items-center gap-1 px-2 py-1 rounded-md transition-colors ${
              deviceMode === 'desktop'
                ? 'bg-slate-800 text-white font-medium shadow-sm'
                : 'text-slate-600 hover:text-slate-900 hover:bg-slate-100'
            }`}
            title="Desktop View"
          >
            <Monitor className="w-3.5 h-3.5" />
            <span>Desktop</span>
          </button>
          <button
            type="button"
            onClick={() => setDeviceMode('mobile')}
            className={`flex items-center gap-1 px-2 py-1 rounded-md transition-colors ${
              deviceMode === 'mobile'
                ? 'bg-slate-800 text-white font-medium shadow-sm'
                : 'text-slate-600 hover:text-slate-900 hover:bg-slate-100'
            }`}
            title="Mobile View (375px)"
          >
            <Smartphone className="w-3.5 h-3.5" />
            <span>Mobile</span>
          </button>
        </div>
      </div>

      {/* Frame Container */}
      <div className="flex-1 flex justify-center items-start p-4 overflow-y-auto max-h-[620px] bg-slate-100">
        <div
          className={`transition-all duration-300 bg-white rounded-lg shadow-sm border border-slate-200/80 overflow-hidden ${
            deviceMode === 'mobile' ? 'w-[375px] shrink-0' : 'w-full max-w-2xl'
          }`}
        >
          <iframe
            srcDoc={htmlContent}
            title={title}
            sandbox="allow-same-origin"
            className="w-full border-0 block"
            style={{ minHeight, height: '480px' }}
          />
        </div>
      </div>
    </div>
  );
};
