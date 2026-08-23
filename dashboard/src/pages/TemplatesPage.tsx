import React, { useEffect, useState } from 'react';
import { api } from '../api/client';
import { EventTemplate } from '../types';
import { Badge } from '../components/common/Badge';
import { Drawer } from '../components/common/Drawer';
import { HtmlPreviewIframe } from '../components/common/HtmlPreviewIframe';
import { TableSkeleton } from '../components/common/Skeleton';
import { useToast } from '../context/ToastContext';
import {
  Eye,
  ShieldCheck,
  RefreshCw,
  AlertCircle,
} from 'lucide-react';


export const TemplatesPage: React.FC = () => {
  const [templates, setTemplates] = useState<EventTemplate[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Selected template for sample preview
  const [selectedTemplate, setSelectedTemplate] = useState<EventTemplate | null>(null);
  const [isDrawerOpen, setIsDrawerOpen] = useState(false);

  // Toggle loading tracker: templateId -> boolean
  const [togglingIds, setTogglingIds] = useState<Record<string, boolean>>({});

  const toast = useToast();

  const fetchTemplates = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.getTemplates();
      setTemplates(data);
    } catch (err: any) {
      setError(err.message || 'Failed to load templates');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchTemplates();
  }, []);

  const handleToggleActive = async (template: EventTemplate, e?: React.MouseEvent) => {
    if (e) e.stopPropagation();

    const newActive = !template.is_active;
    setTogglingIds((prev) => ({ ...prev, [template.id]: true }));

    try {
      const updated = await api.updateTemplate(template.id, newActive);
      setTemplates((prev) =>
        prev.map((t) => (t.id === template.id ? updated : t))
      );
      toast.success(
        'Template Updated',
        `${template.variant_key} is now ${newActive ? 'active' : 'inactive'}.`
      );
      if (selectedTemplate && selectedTemplate.id === template.id) {
        setSelectedTemplate(updated);
      }
    } catch (err: any) {
      toast.error('Failed to update template', err.message);
    } finally {
      setTogglingIds((prev) => ({ ...prev, [template.id]: false }));
    }
  };

  const handleRowClick = (template: EventTemplate) => {
    setSelectedTemplate(template);
    setIsDrawerOpen(true);
  };

  // Generate sample substituted HTML for realistic preview
  const generateSamplePreview = (template: EventTemplate): { subject: string; body: string } => {
    const sampleContext: Record<string, string> = {
      '{{ name }}': 'Jane Doe',
      '{{ preferred_name }}': 'Jane',
      '{{ years }}': template.variant_key.includes('10') ? '10' : template.variant_key.includes('5') ? '5' : '3',
      '{{ photo_url }}': 'https://images.unsplash.com/photo-1494790108377-be9c29b29330?w=240&h=240&fit=crop&crop=face',
      '{{ department }}': 'Platform Engineering',
      '{{ company_name }}': 'Acme Corp',
      '{{ company_logo_url }}': 'https://dummyimage.com/120x32/ff6f91/ffffff&text=ACME',
    };

    let sampleSubject = template.subject_line;
    let sampleBody = template.html_body;

    // Replace basic placeholders for visual preview
    Object.entries(sampleContext).forEach(([key, val]) => {
      sampleSubject = sampleSubject.split(key).join(val);
      sampleBody = sampleBody.split(key).join(val);
    });

    // Clean up simple Jinja conditional tags like {% if department %}...{% endif %}
    sampleBody = sampleBody.replace(/{%\s*if\s+department\s*%}/g, '');
    sampleBody = sampleBody.replace(/{%\s*endif\s*%}/g, '');
    sampleBody = sampleBody.replace(/{%\s*if\s+years\s*!=\s*1\s*%}s{%\s*endif\s*%}/g, 's');

    return { subject: sampleSubject, body: sampleBody };
  };

  return (
    <div className="space-y-6">
      {/* Top Banner Notice: Immutability by Design */}
      <div className="p-4 sm:p-5 rounded-2xl bg-indigo-50/80 border border-indigo-200/80 flex items-start gap-4">
        <div className="w-9 h-9 rounded-xl bg-indigo-100 text-indigo-700 flex items-center justify-center shrink-0 mt-0.5">
          <ShieldCheck className="w-5 h-5" />
        </div>
        <div className="space-y-1 text-xs text-indigo-950 flex-1">
          <h4 className="font-bold text-sm text-indigo-900">Code-Reviewed Template Management</h4>
          <p className="leading-relaxed text-indigo-800">
            Email templates are static Jinja2 HTML layouts version-controlled in the repository. To ensure
            zero unexpected formatting breaks or security risks, template text cannot be edited directly in the dashboard.
            <span className="font-semibold ml-1">
              To change template HTML or copy, submit a Git pull request to engineering.
            </span>
          </p>
        </div>
      </div>

      {/* Templates List */}
      <div className="p-5 rounded-2xl bg-white border border-slate-100 shadow-sm space-y-4">
        <div className="flex items-center justify-between">
          <div>
            <h3 className="text-base font-bold text-slate-800">Seeded Notification Templates</h3>
            <p className="text-xs text-slate-500 mt-0.5">
              Control active status and preview static layouts with sample employee data
            </p>
          </div>
          <button
            type="button"
            onClick={fetchTemplates}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl border border-slate-200 bg-white hover:bg-slate-50 text-slate-700 text-xs font-semibold shadow-xs transition-colors"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
            <span>Refresh</span>
          </button>
        </div>

        {loading ? (
          <TableSkeleton rows={4} cols={5} />
        ) : error ? (
          <div className="p-8 text-center text-rose-600 text-xs">
            <AlertCircle className="w-8 h-8 mx-auto mb-2 text-rose-500" />
            <p className="font-semibold">{error}</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs text-slate-600">
              <thead className="bg-slate-50/80 border-b border-slate-100 text-[11px] uppercase tracking-wider font-semibold text-slate-500">
                <tr>
                  <th className="px-4 py-3.5">Event Type</th>
                  <th className="px-4 py-3.5">Variant Key</th>
                  <th className="px-4 py-3.5">Subject Template</th>
                  <th className="px-4 py-3.5">Status</th>
                  <th className="px-4 py-3.5 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {templates.map((template) => {
                  const isToggling = togglingIds[template.id] || false;
                  return (
                    <tr
                      key={template.id}
                      onClick={() => handleRowClick(template)}
                      className="hover:bg-slate-50/80 cursor-pointer transition-colors group"
                    >
                      {/* Event Type */}
                      <td className="px-4 py-3.5 whitespace-nowrap">
                        <Badge eventType={template.event_type} />
                      </td>

                      {/* Variant Key */}
                      <td className="px-4 py-3.5 font-mono font-semibold text-slate-800 whitespace-nowrap">
                        {template.variant_key}
                      </td>

                      {/* Subject Line */}
                      <td className="px-4 py-3.5 text-slate-700 font-mono text-xs max-w-sm truncate">
                        {template.subject_line}
                      </td>

                      {/* Status Toggle */}
                      <td className="px-4 py-3.5 whitespace-nowrap" onClick={(e) => e.stopPropagation()}>
                        <button
                          type="button"
                          onClick={(e) => handleToggleActive(template, e)}
                          disabled={isToggling}
                          className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold border transition-all ${
                            template.is_active
                              ? 'bg-emerald-50 text-emerald-700 border-emerald-200 hover:bg-emerald-100'
                              : 'bg-slate-100 text-slate-500 border-slate-200 hover:bg-slate-200'
                          }`}
                        >
                          <span
                            className={`w-2 h-2 rounded-full ${
                              template.is_active ? 'bg-emerald-500' : 'bg-slate-400'
                            }`}
                          />
                          <span>{template.is_active ? 'Active' : 'Disabled'}</span>
                        </button>
                      </td>

                      {/* Actions */}
                      <td className="px-4 py-3.5 text-right whitespace-nowrap" onClick={(e) => e.stopPropagation()}>
                        <button
                          type="button"
                          onClick={() => handleRowClick(template)}
                          className="inline-flex items-center gap-1 px-3 py-1 rounded-lg border border-slate-200 text-slate-700 hover:bg-slate-50 text-xs font-semibold transition-colors"
                        >
                          <Eye className="w-3.5 h-3.5 text-slate-400" />
                          <span>Preview</span>
                        </button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Template Sample Preview Drawer */}
      <Drawer
        isOpen={isDrawerOpen}
        onClose={() => setIsDrawerOpen(false)}
        title={selectedTemplate ? `Template: ${selectedTemplate.variant_key}` : 'Template Preview'}
        subtitle="Static Jinja2 template preview with sample placeholder data"
        width="xl"
      >
        {selectedTemplate && (
          <div className="space-y-6">
            {/* Status & Fallback Info Card */}
            <div className="flex items-center justify-between p-4 rounded-xl bg-slate-50 border border-slate-200">
              <div className="space-y-0.5">
                <div className="flex items-center gap-2">
                  <Badge eventType={selectedTemplate.event_type} size="md" />
                  <Badge status={selectedTemplate.is_active ? 'active' : 'inactive'} size="md" />
                </div>
                <div className="text-[11px] text-slate-500 pt-1">
                  Fallback policy: If deactivated, milestone anniversaries automatically fall back to the generic anniversary default template.
                </div>
              </div>

              <button
                type="button"
                onClick={() => handleToggleActive(selectedTemplate)}
                disabled={togglingIds[selectedTemplate.id]}
                className={`inline-flex items-center gap-1.5 px-3.5 py-2 rounded-xl text-xs font-semibold transition-colors ${
                  selectedTemplate.is_active
                    ? 'bg-rose-50 text-rose-700 hover:bg-rose-100 border border-rose-200'
                    : 'bg-emerald-600 text-white hover:bg-emerald-700 shadow-sm'
                }`}
              >
                {selectedTemplate.is_active ? 'Disable Template' : 'Activate Template'}
              </button>
            </div>

            {/* Subject Line with Sample Data */}
            <div>
              <label className="block text-xs font-semibold uppercase tracking-wider text-slate-500 mb-1">
                Subject Line (With Sample Data)
              </label>
              <div className="p-3 rounded-xl bg-slate-100 border border-slate-200 text-xs font-medium text-slate-800">
                {generateSamplePreview(selectedTemplate).subject}
              </div>
              <div className="text-[11px] text-slate-400 mt-1 font-mono">
                Raw: {selectedTemplate.subject_line}
              </div>
            </div>

            {/* Rendered Sample Preview */}
            <div>
              <label className="block text-xs font-semibold uppercase tracking-wider text-slate-500 mb-1.5">
                Live Sample Render (Sandboxed iFrame)
              </label>
              <HtmlPreviewIframe
                htmlContent={generateSamplePreview(selectedTemplate).body}
                title={`Preview ${selectedTemplate.variant_key}`}
                minHeight="440px"
              />
            </div>
          </div>
        )}
      </Drawer>
    </div>
  );
};
