import React, { useEffect, useState } from 'react';
import { api } from '../api/client';
import { EventTemplate, EventType, SuperAdminOrg, TemplateCreatePayload, TemplateUpdatePayload } from '../types';
import { Badge } from '../components/common/Badge';
import { Drawer } from '../components/common/Drawer';
import { Modal } from '../components/common/Modal';
import { HtmlPreviewIframe } from '../components/common/HtmlPreviewIframe';
import { TableSkeleton } from '../components/common/Skeleton';
import { useAuth } from '../context/AuthContext';
import { useToast } from '../context/ToastContext';
import {
  Eye,
  RefreshCw,
  AlertCircle,
  Plus,
  Edit2,
  Trash2,
  Star,
  Sparkles,
  Code2,
  CheckCircle2,
  HelpCircle,
  FileCode,
  Building2,
} from 'lucide-react';

export const TemplatesPage: React.FC = () => {
  const [templates, setTemplates] = useState<EventTemplate[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Selected template for sample preview drawer
  const [selectedTemplate, setSelectedTemplate] = useState<EventTemplate | null>(null);
  const [isDrawerOpen, setIsDrawerOpen] = useState(false);

  // Create / Edit Modal state
  const [isEditorOpen, setIsEditorOpen] = useState(false);
  const [editingTemplate, setEditingTemplate] = useState<EventTemplate | null>(null);
  const [editorSubmitting, setEditorSubmitting] = useState(false);
  const [editorTab, setEditorTab] = useState<'code' | 'preview'>('code');

  // Form State
  const [formName, setFormName] = useState('');
  const [formEventType, setFormEventType] = useState<EventType>('birthday');
  const [formSubject, setFormSubject] = useState('');
  const [formHtml, setFormHtml] = useState('');
  const [formIsDefault, setFormIsDefault] = useState(false);
  const [formIsActive, setFormIsActive] = useState(true);

  // Live modal preview state
  const [modalPreviewHtml, setModalPreviewHtml] = useState<string>('');
  const [modalPreviewSubject, setModalPreviewSubject] = useState<string>('');
  const [modalPreviewLoading, setModalPreviewLoading] = useState(false);
  const [modalPreviewError, setModalPreviewError] = useState<string | null>(null);

  // Toggle / action loading trackers
  const [togglingIds, setTogglingIds] = useState<Record<string, boolean>>({});
  const [deletingId, setDeletingId] = useState<string | null>(null);

  const toast = useToast();
  const { activeOrg, isSuperAdmin, selectedTenantId, switchTenant } = useAuth();
  const [tenantList, setTenantList] = useState<SuperAdminOrg[]>([]);

  useEffect(() => {
    if (isSuperAdmin) {
      api.getSuperAdminOrganizations()
        .then((data) => {
          setTenantList(data);
          if (!activeOrg && data.length > 0) {
            switchTenant(data[0].id, data[0] as any);
          }
        })
        .catch(() => {});
    }
  }, [isSuperAdmin]);

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
  }, [selectedTenantId, activeOrg?.id]);

  const openCreateModal = () => {
    setEditingTemplate(null);
    setFormName('');
    setFormEventType('birthday');
    setFormSubject('🎉 Happy Birthday, {{ name }}!');
    setFormHtml(
      `<div style="font-family: sans-serif; max-width: 600px; margin: 0 auto; padding: 24px; background: #ffffff; border-radius: 12px; border: 1px solid #e2e8f0; text-align: center;">
  <h1 style="color: #e11d48; margin-bottom: 8px;">Happy Birthday, {{ name }}! 🎂</h1>
  <p style="color: #475569; font-size: 15px; line-height: 1.6;">
    Wishing you a wonderful day filled with happiness and joy! Thank you for being a fantastic part of the {{ company_name }} team.
  </p>
  {% if photo_url %}
  <div style="margin: 20px 0;">
    <img src="{{ photo_url }}" alt="{{ name }}" style="width: 100px; height: 100px; border-radius: 50%; object-fit: cover; border: 3px solid #fecdd3;" />
  </div>
  {% endif %}
  <div style="margin-top: 24px; font-size: 13px; color: #94a3b8;">
    Celebrated by {{ company_name }}
  </div>
</div>`
    );
    setFormIsDefault(false);
    setFormIsActive(true);
    setEditorTab('code');
    setModalPreviewError(null);
    setIsEditorOpen(true);
  };

  const openEditModal = (template: EventTemplate, e?: React.MouseEvent) => {
    if (e) e.stopPropagation();
    setEditingTemplate(template);
    setFormName(template.name || template.variant_key);
    setFormEventType(template.event_type);
    setFormSubject(template.subject_line);
    setFormHtml(template.html_body);
    setFormIsDefault(template.is_default);
    setFormIsActive(template.is_active);
    setEditorTab('code');
    setModalPreviewError(null);
    setIsEditorOpen(true);
  };

  const insertVariable = (variable: string) => {
    setFormHtml((prev) => prev + variable);
  };

  const handleUpdatePreview = async () => {
    setModalPreviewLoading(true);
    setModalPreviewError(null);
    try {
      const res = await api.previewTemplate({
        event_type: formEventType,
        subject_line: formSubject,
        html_body: formHtml,
      });
      setModalPreviewSubject(res.rendered_subject);
      setModalPreviewHtml(res.rendered_html);
    } catch (err: any) {
      setModalPreviewError(err.message || 'Failed to render preview');
    } finally {
      setModalPreviewLoading(false);
    }
  };

  useEffect(() => {
    if (editorTab === 'preview' && isEditorOpen) {
      handleUpdatePreview();
    }
  }, [editorTab]);

  const handleSaveTemplate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!formName.trim() || !formSubject.trim() || !formHtml.trim()) {
      toast.error('Validation Error', 'Please fill in all template fields.');
      return;
    }

    setEditorSubmitting(true);
    try {
      if (editingTemplate) {
        const payload: TemplateUpdatePayload = {
          name: formName.trim(),
          subject_line: formSubject.trim(),
          html_body: formHtml,
          is_default: formIsDefault,
          is_active: formIsActive,
        };
        const updated = await api.updateTemplate(editingTemplate.id, payload);
        toast.success('Template Updated', `"${updated.name || updated.variant_key}" saved successfully.`);
        if (selectedTemplate?.id === updated.id) {
          setSelectedTemplate(updated);
        }
      } else {
        const payload: TemplateCreatePayload = {
          name: formName.trim(),
          event_type: formEventType,
          subject_line: formSubject.trim(),
          html_body: formHtml,
          is_default: formIsDefault,
          is_active: formIsActive,
        };
        const created = await api.createTemplate(payload);
        toast.success('Template Created', `"${created.name}" has been configured.`);
      }
      setIsEditorOpen(false);
      fetchTemplates();
    } catch (err: any) {
      toast.error('Save Failed', err.message);
    } finally {
      setEditorSubmitting(false);
    }
  };

  const handleSetAsDefault = async (template: EventTemplate, e?: React.MouseEvent) => {
    if (e) e.stopPropagation();
    if (template.is_default) return;

    try {
      await api.updateTemplate(template.id, { is_default: true, is_active: true });
      toast.success(
        'Default Template Set',
        `"${template.name || template.variant_key}" is now the default for ${template.event_type === 'birthday' ? 'Birthdays' : 'Work Anniversaries'}.`
      );
      fetchTemplates();
      if (selectedTemplate?.id === template.id) {
        setSelectedTemplate({ ...selectedTemplate, is_default: true, is_active: true });
      }
    } catch (err: any) {
      toast.error('Update Failed', err.message);
    }
  };

  const handleToggleActive = async (template: EventTemplate, e?: React.MouseEvent) => {
    if (e) e.stopPropagation();

    const newActive = !template.is_active;
    setTogglingIds((prev) => ({ ...prev, [template.id]: true }));

    try {
      const updated = await api.updateTemplate(template.id, { is_active: newActive });
      setTemplates((prev) => prev.map((t) => (t.id === template.id ? updated : t)));
      toast.success(
        'Template Status Changed',
        `"${template.name || template.variant_key}" is now ${newActive ? 'active' : 'disabled'}.`
      );
      if (selectedTemplate?.id === template.id) {
        setSelectedTemplate(updated);
      }
    } catch (err: any) {
      toast.error('Failed to update status', err.message);
    } finally {
      setTogglingIds((prev) => ({ ...prev, [template.id]: false }));
    }
  };

  const handleDeleteTemplate = async (template: EventTemplate, e?: React.MouseEvent) => {
    if (e) e.stopPropagation();

    if (template.is_default) {
      toast.error(
        'Cannot Delete Default Template',
        'Please designate another template as default before deleting this one.'
      );
      return;
    }

    if (!window.confirm(`Are you sure you want to delete "${template.name || template.variant_key}"? Any employees assigned this template will revert to the organization default.`)) {
      return;
    }

    setDeletingId(template.id);
    try {
      await api.deleteTemplate(template.id);
      toast.success('Template Deleted', `"${template.name || template.variant_key}" has been removed.`);
      if (selectedTemplate?.id === template.id) {
        setIsDrawerOpen(false);
        setSelectedTemplate(null);
      }
      fetchTemplates();
    } catch (err: any) {
      toast.error('Delete Failed', err.message);
    } finally {
      setDeletingId(null);
    }
  };

  const handleRowClick = (template: EventTemplate) => {
    setSelectedTemplate(template);
    setIsDrawerOpen(true);
  };

  // Realistic sample context substitution for drawer preview
  const generateSamplePreview = (template: EventTemplate): { subject: string; body: string } => {
    const companyName = activeOrg?.name || 'Acme Corp';
    const sampleContext: Record<string, string> = {
      '{{ name }}': 'Jane Doe',
      '{{ preferred_name }}': 'Jane',
      '{{ years }}': template.variant_key.includes('10') ? '10' : template.variant_key.includes('5') ? '5' : '3',
      '{{ photo_url }}': 'https://images.unsplash.com/photo-1494790108377-be9c29b29330?w=240&h=240&fit=crop&crop=face',
      '{{ department }}': 'Product Engineering',
      '{{ company_name }}': companyName,
      '{{ company_logo_url }}': activeOrg?.company_logo_url || `https://dummyimage.com/120x32/ff6f91/ffffff&text=${encodeURIComponent(companyName.substring(0, 10))}`,
    };

    let sampleSubject = template.subject_line;
    let sampleBody = template.html_body;

    Object.entries(sampleContext).forEach(([key, val]) => {
      sampleSubject = sampleSubject.split(key).join(val);
      sampleBody = sampleBody.split(key).join(val);
    });

    sampleBody = sampleBody.replace(/{%\s*if\s+department\s*%}/g, '');
    sampleBody = sampleBody.replace(/{%\s*endif\s*%}/g, '');
    sampleBody = sampleBody.replace(/{%\s*if\s+photo_url\s*%}/g, '');
    sampleBody = sampleBody.replace(/{%\s*if\s+years\s*!=\s*1\s*%}s{%\s*endif\s*%}/g, 's');

    return { subject: sampleSubject, body: sampleBody };
  };

  return (
    <div className="space-y-6">
      {/* Top Banner Notice */}
      <div className="p-4 sm:p-5 rounded-2xl bg-gradient-to-r from-rose-50 to-pink-50 border border-rose-100 flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div className="flex items-start gap-3.5">
          <div className="w-10 h-10 rounded-xl bg-rose-100 text-rose-600 flex items-center justify-center shrink-0 mt-0.5 shadow-sm">
            <Sparkles className="w-5 h-5" />
          </div>
          <div className="space-y-1 text-xs text-rose-950 flex-1">
            <div className="flex items-center gap-2 flex-wrap">
              <h4 className="font-bold text-sm text-rose-900">Custom Celebration Branding & Templates</h4>
              {activeOrg && (
                <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full bg-rose-200/70 text-rose-900 font-bold text-[11px] border border-rose-300/60">
                  <Building2 className="w-3 h-3 text-rose-700" />
                  <span>Tenant: {activeOrg.name}</span>
                </span>
              )}
            </div>
            <p className="leading-relaxed text-rose-800">
              Create and manage multiple HTML email designs for Birthdays and Work Anniversaries.
              Each tenant maintains its own isolated catalog of templates. Configure custom HTML designs with live preview, set an <strong>Organization Default</strong>, or assign <strong>specific templates</strong> to individual members.
            </p>
          </div>
        </div>

        <div className="flex items-center gap-3 shrink-0 flex-wrap">
          {isSuperAdmin && tenantList.length > 0 && (
            <div className="flex items-center gap-1.5 bg-white px-3 py-1.5 rounded-xl border border-rose-200 shadow-xs">
              <Building2 className="w-4 h-4 text-purple-600 shrink-0" />
              <span className="text-xs font-semibold text-slate-700 whitespace-nowrap">Tenant:</span>
              <select
                value={activeOrg?.id || ''}
                onChange={(e) => {
                  const target = tenantList.find((o) => o.id === e.target.value);
                  if (target) {
                    switchTenant(target.id, target as any);
                  }
                }}
                className="bg-transparent text-xs font-bold text-slate-900 border-none outline-none focus:ring-0 cursor-pointer pr-1"
              >
                {tenantList.map((org) => (
                  <option key={org.id} value={org.id}>
                    {org.name} {org.is_demo ? '(Demo)' : ''}
                  </option>
                ))}
              </select>
            </div>
          )}

          <button
            type="button"
            onClick={openCreateModal}
            className="shrink-0 inline-flex items-center gap-2 px-4 py-2.5 rounded-xl bg-gradient-to-r from-rose-600 to-pink-600 hover:from-rose-700 hover:to-pink-700 text-white text-xs font-semibold shadow-md shadow-rose-950/10 transition-all active:scale-98 cursor-pointer"
          >
            <Plus className="w-4 h-4" />
            <span>Configure New Template</span>
          </button>
        </div>
      </div>

      {/* Templates Directory Table */}
      <div className="p-5 rounded-2xl bg-white border border-slate-100 shadow-sm space-y-4">
        <div className="flex items-center justify-between">
          <div>
            <h3 className="text-base font-bold text-slate-800">
              {activeOrg ? `${activeOrg.name} — Templates Catalog` : 'Templates Catalog'}
            </h3>
            <p className="text-xs text-slate-500 mt-0.5">
              Manage email designs, assign organization defaults, and preview layouts
            </p>
          </div>
          <button
            type="button"
            onClick={fetchTemplates}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl border border-slate-200 bg-white hover:bg-slate-50 text-slate-700 text-xs font-semibold shadow-xs transition-colors cursor-pointer"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
            <span>Refresh</span>
          </button>
        </div>

        {loading ? (
          <TableSkeleton rows={4} cols={5} />
        ) : error ? (
          <div className="p-8 text-center text-xs">
            <AlertCircle className="w-8 h-8 mx-auto mb-2 text-rose-500" />
            <p className="font-semibold text-rose-600 mb-1">{error}</p>
            {error.toLowerCase().includes('no active organization') && tenantList.length > 0 && (
              <div className="mt-4 flex flex-col items-center gap-2">
                <p className="text-slate-500 text-xs">Select an organization to load its templates:</p>
                <div className="flex gap-2">
                  {tenantList.slice(0, 3).map((org) => (
                    <button
                      key={org.id}
                      type="button"
                      onClick={() => switchTenant(org.id, org as any)}
                      className="px-3 py-1.5 rounded-lg bg-rose-50 text-rose-700 hover:bg-rose-100 border border-rose-200 text-xs font-semibold transition-colors"
                    >
                      {org.name}
                    </button>
                  ))}
                </div>
              </div>
            )}
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs text-slate-600 border-collapse">
              <thead className="bg-slate-50/80 border-b border-slate-100 text-[11px] uppercase tracking-wider font-semibold text-slate-500">
                <tr>
                  <th className="px-4 py-3.5">Template Name</th>
                  <th className="px-4 py-3.5">Event Type</th>
                  <th className="px-4 py-3.5 text-center">Default For Org</th>
                  <th className="px-4 py-3.5">Subject Template</th>
                  <th className="px-4 py-3.5">Status</th>
                  <th className="px-4 py-3.5 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {templates.map((template) => {
                  const isToggling = togglingIds[template.id] || false;
                  const isDeleting = deletingId === template.id;

                  return (
                    <tr
                      key={template.id}
                      onClick={() => handleRowClick(template)}
                      className="hover:bg-slate-50/80 cursor-pointer transition-colors group"
                    >
                      {/* Name & Key */}
                      <td className="px-4 py-3.5 whitespace-nowrap">
                        <div className="flex items-center gap-2">
                          <FileCode className="w-4 h-4 text-slate-400 group-hover:text-rose-500 transition-colors" />
                          <div>
                            <p className="font-bold text-slate-900 text-xs">
                              {template.name || template.variant_key}
                            </p>
                            <p className="text-[10px] font-mono text-slate-400">
                              key: {template.variant_key}
                            </p>
                          </div>
                        </div>
                      </td>

                      {/* Event Type */}
                      <td className="px-4 py-3.5 whitespace-nowrap">
                        <Badge eventType={template.event_type} />
                      </td>

                      {/* Default Badge / Setter */}
                      <td className="px-4 py-3.5 text-center whitespace-nowrap" onClick={(e) => e.stopPropagation()}>
                        {template.is_default ? (
                          <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full bg-amber-50 text-amber-800 border border-amber-200 text-[11px] font-bold">
                            <Star className="w-3 h-3 fill-amber-400 text-amber-500" />
                            <span>Default</span>
                          </span>
                        ) : (
                          <button
                            type="button"
                            onClick={(e) => handleSetAsDefault(template, e)}
                            className="text-[11px] font-medium text-slate-400 hover:text-amber-600 hover:underline cursor-pointer"
                            title="Set as organization default template"
                          >
                            Set as Default
                          </button>
                        )}
                      </td>

                      {/* Subject Line */}
                      <td className="px-4 py-3.5 text-slate-700 font-mono text-xs max-w-xs truncate">
                        {template.subject_line}
                      </td>

                      {/* Status Toggle */}
                      <td className="px-4 py-3.5 whitespace-nowrap" onClick={(e) => e.stopPropagation()}>
                        <button
                          type="button"
                          onClick={(e) => handleToggleActive(template, e)}
                          disabled={isToggling}
                          className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold border transition-all cursor-pointer ${
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
                        <div className="inline-flex items-center gap-1.5">
                          <button
                            type="button"
                            onClick={() => handleRowClick(template)}
                            className="inline-flex items-center gap-1 px-2.5 py-1.5 rounded-lg border border-slate-200 text-slate-700 hover:bg-slate-100 text-xs font-semibold transition-colors cursor-pointer"
                            title="Preview live design"
                          >
                            <Eye className="w-3.5 h-3.5 text-slate-400" />
                            <span>Preview</span>
                          </button>

                          <button
                            type="button"
                            onClick={(e) => openEditModal(template, e)}
                            className="inline-flex items-center gap-1 px-2.5 py-1.5 rounded-lg border border-slate-200 text-slate-700 hover:bg-slate-100 text-xs font-semibold transition-colors cursor-pointer"
                            title="Edit template content"
                          >
                            <Edit2 className="w-3.5 h-3.5 text-slate-400" />
                            <span>Edit</span>
                          </button>

                          <button
                            type="button"
                            onClick={(e) => handleDeleteTemplate(template, e)}
                            disabled={template.is_default || isDeleting}
                            className={`inline-flex items-center p-1.5 rounded-lg border text-xs transition-colors ${
                              template.is_default
                                ? 'border-slate-200 text-slate-300 cursor-not-allowed'
                                : 'border-slate-200 text-slate-400 hover:text-rose-600 hover:bg-rose-50 hover:border-rose-200 cursor-pointer'
                            }`}
                            title={template.is_default ? 'Cannot delete default template' : 'Delete template'}
                          >
                            <Trash2 className="w-3.5 h-3.5" />
                          </button>
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Template Create & Edit Modal */}
      <Modal
        isOpen={isEditorOpen}
        onClose={() => setIsEditorOpen(false)}
        title={editingTemplate ? `Edit Template: ${editingTemplate.name || editingTemplate.variant_key}` : 'Configure New Template'}
        maxWidth="2xl"
      >
        <form onSubmit={handleSaveTemplate} className="space-y-4">
          {/* Tab Switcher: Editor vs Live Preview */}
          <div className="flex items-center justify-between border-b border-slate-200 pb-2">
            <div className="flex items-center gap-2">
              <button
                type="button"
                onClick={() => setEditorTab('code')}
                className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-semibold transition-colors ${
                  editorTab === 'code'
                    ? 'bg-slate-900 text-white shadow-xs'
                    : 'text-slate-600 hover:bg-slate-100'
                }`}
              >
                <Code2 className="w-3.5 h-3.5" />
                <span>Template Editor</span>
              </button>

              <button
                type="button"
                onClick={() => setEditorTab('preview')}
                className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-semibold transition-colors ${
                  editorTab === 'preview'
                    ? 'bg-rose-600 text-white shadow-xs'
                    : 'text-slate-600 hover:bg-slate-100'
                }`}
              >
                <Eye className="w-3.5 h-3.5" />
                <span>Live Design Preview</span>
              </button>
            </div>

            {editorTab === 'preview' && (
              <button
                type="button"
                onClick={handleUpdatePreview}
                className="text-xs text-rose-600 hover:underline inline-flex items-center gap-1"
              >
                <RefreshCw className={`w-3 h-3 ${modalPreviewLoading ? 'animate-spin' : ''}`} />
                <span>Refresh Preview</span>
              </button>
            )}
          </div>

          {editorTab === 'code' ? (
            <div className="space-y-4">
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">
                    Template Name *
                  </label>
                  <input
                    type="text"
                    required
                    value={formName}
                    onChange={(e) => setFormName(e.target.value)}
                    placeholder="e.g. Modern Executive Birthday"
                    className="w-full px-3 py-2 border border-slate-200 rounded-xl text-xs focus:ring-2 focus:ring-rose-500/20 focus:border-rose-500"
                  />
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">
                    Event Type *
                  </label>
                  <select
                    value={formEventType}
                    disabled={Boolean(editingTemplate)}
                    onChange={(e) => setFormEventType(e.target.value as EventType)}
                    className="w-full px-3 py-2 border border-slate-200 rounded-xl text-xs bg-white focus:ring-2 focus:ring-rose-500/20 focus:border-rose-500 disabled:bg-slate-100 disabled:text-slate-500"
                  >
                    <option value="birthday">Birthday</option>
                    <option value="work_anniversary">Work Anniversary</option>
                  </select>
                </div>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">
                  Email Subject Line *
                </label>
                <input
                  type="text"
                  required
                  value={formSubject}
                  onChange={(e) => setFormSubject(e.target.value)}
                  placeholder="🎉 Happy Birthday, {{ name }}!"
                  className="w-full px-3 py-2 font-mono text-xs border border-slate-200 rounded-xl focus:ring-2 focus:ring-rose-500/20 focus:border-rose-500"
                />
              </div>

              {/* Tag Insertion Helper */}
              <div>
                <div className="flex items-center justify-between mb-1.5">
                  <label className="block text-xs font-semibold text-slate-700">
                    HTML Template Body *
                  </label>
                  <span className="text-[11px] text-slate-400">Click to insert placeholder:</span>
                </div>
                <div className="flex flex-wrap gap-1.5 mb-2">
                  {['{{ name }}', '{{ preferred_name }}', '{{ years }}', '{{ department }}', '{{ photo_url }}', '{{ company_name }}'].map((chip) => (
                    <button
                      key={chip}
                      type="button"
                      onClick={() => insertVariable(chip)}
                      className="px-2 py-0.5 rounded-lg bg-slate-100 hover:bg-slate-200 text-slate-700 font-mono text-[11px] border border-slate-200 transition-colors"
                    >
                      + {chip}
                    </button>
                  ))}
                </div>
                <textarea
                  required
                  rows={12}
                  value={formHtml}
                  onChange={(e) => setFormHtml(e.target.value)}
                  placeholder="Paste or write HTML email content..."
                  className="w-full p-3 font-mono text-xs border border-slate-200 rounded-xl bg-slate-950 text-slate-100 focus:outline-none focus:ring-2 focus:ring-rose-500/40"
                />
              </div>

              {/* Flags */}
              <div className="flex items-center gap-6 pt-2 border-t border-slate-100">
                <label className="flex items-center gap-2 cursor-pointer select-none">
                  <input
                    type="checkbox"
                    checked={formIsDefault}
                    onChange={(e) => setFormIsDefault(e.target.checked)}
                    className="w-4 h-4 rounded text-rose-600 focus:ring-rose-500"
                  />
                  <span className="text-xs font-medium text-slate-700">
                    Set as Organization Default for {formEventType === 'birthday' ? 'Birthdays' : 'Work Anniversaries'}
                  </span>
                </label>

                <label className="flex items-center gap-2 cursor-pointer select-none">
                  <input
                    type="checkbox"
                    checked={formIsActive}
                    onChange={(e) => setFormIsActive(e.target.checked)}
                    className="w-4 h-4 rounded text-emerald-600 focus:ring-emerald-500"
                  />
                  <span className="text-xs font-medium text-slate-700">
                    Active (Available for delivery)
                  </span>
                </label>
              </div>
            </div>
          ) : (
            <div className="space-y-4">
              {modalPreviewError && (
                <div className="p-3 rounded-xl bg-rose-50 border border-rose-200 text-rose-700 text-xs flex items-center gap-2">
                  <AlertCircle className="w-4 h-4 shrink-0" />
                  <span>{modalPreviewError}</span>
                </div>
              )}

              <div>
                <label className="block text-[11px] font-bold uppercase tracking-wider text-slate-400 mb-1">
                  Subject Preview
                </label>
                <div className="p-2.5 rounded-xl bg-slate-50 border border-slate-200 text-xs font-semibold text-slate-800">
                  {modalPreviewSubject || formSubject}
                </div>
              </div>

              <div>
                <label className="block text-[11px] font-bold uppercase tracking-wider text-slate-400 mb-1">
                  Rendered Email Body
                </label>
                <HtmlPreviewIframe
                  htmlContent={modalPreviewHtml || formHtml}
                  title="Design Preview Sandbox"
                  minHeight="380px"
                />
              </div>
            </div>
          )}

          {/* Modal Footer */}
          <div className="flex items-center justify-end gap-3 pt-4 border-t border-slate-200">
            <button
              type="button"
              onClick={() => setIsEditorOpen(false)}
              className="px-4 py-2 border border-slate-200 hover:bg-slate-50 text-slate-700 text-xs font-semibold rounded-xl transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={editorSubmitting}
              className="px-5 py-2 bg-gradient-to-r from-rose-600 to-pink-600 hover:from-rose-700 hover:to-pink-700 disabled:opacity-50 text-white text-xs font-semibold rounded-xl shadow-md shadow-rose-950/10 transition-all cursor-pointer"
            >
              {editorSubmitting ? 'Saving...' : editingTemplate ? 'Update Template' : 'Create Template'}
            </button>
          </div>
        </form>
      </Modal>

      {/* Template Sample Preview Drawer */}
      <Drawer
        isOpen={isDrawerOpen}
        onClose={() => setIsDrawerOpen(false)}
        title={selectedTemplate ? `Template: ${selectedTemplate.name || selectedTemplate.variant_key}` : 'Template Preview'}
        subtitle="Live rendered email preview with sample employee data"
        width="xl"
      >
        {selectedTemplate && (
          <div className="space-y-6">
            {/* Status & Fallback Info Card */}
            <div className="flex items-center justify-between p-4 rounded-xl bg-slate-50 border border-slate-200">
              <div className="space-y-1">
                <div className="flex items-center gap-2">
                  <Badge eventType={selectedTemplate.event_type} size="md" />
                  <Badge status={selectedTemplate.is_active ? 'active' : 'inactive'} size="md" />
                  {selectedTemplate.is_default && (
                    <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full bg-amber-100 text-amber-800 border border-amber-200 text-[10px] font-bold">
                      <Star className="w-3 h-3 fill-amber-500 text-amber-600" />
                      <span>Default</span>
                    </span>
                  )}
                </div>
                <div className="text-[11px] text-slate-500 pt-0.5">
                  Key: <code className="font-mono text-slate-700">{selectedTemplate.variant_key}</code>
                </div>
              </div>

              <div className="flex items-center gap-2">
                <button
                  type="button"
                  onClick={() => openEditModal(selectedTemplate)}
                  className="inline-flex items-center gap-1 px-3 py-1.5 rounded-xl border border-slate-200 bg-white hover:bg-slate-50 text-slate-700 text-xs font-semibold transition-colors"
                >
                  <Edit2 className="w-3.5 h-3.5 text-slate-400" />
                  <span>Edit</span>
                </button>

                {!selectedTemplate.is_default && (
                  <button
                    type="button"
                    onClick={() => handleSetAsDefault(selectedTemplate)}
                    className="inline-flex items-center gap-1 px-3 py-1.5 rounded-xl bg-amber-500 hover:bg-amber-600 text-white text-xs font-semibold transition-colors shadow-xs"
                  >
                    <Star className="w-3.5 h-3.5 fill-current" />
                    <span>Make Default</span>
                  </button>
                )}
              </div>
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
                title={`Preview ${selectedTemplate.name || selectedTemplate.variant_key}`}
                minHeight="440px"
              />
            </div>
          </div>
        )}
      </Drawer>
    </div>
  );
};
