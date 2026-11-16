import React, { useState, useRef } from 'react';
import { Modal } from './Modal';
import { api } from '../../api/client';
import { CsvImportResponse } from '../../types';
import { useToast } from '../../context/ToastContext';
import { UploadCloud, FileText, CheckCircle, AlertCircle, Download, X } from 'lucide-react';

interface CsvImportModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess: () => void;
}

export const CsvImportModal: React.FC<CsvImportModalProps> = ({ isOpen, onClose, onSuccess }) => {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const [result, setResult] = useState<CsvImportResponse | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const toast = useToast();

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      setSelectedFile(e.target.files[0]);
      setResult(null);
    }
  };

  const handleDownloadSample = () => {
    const sampleCsv = `Employee ID,Full Name,Preferred Name,Email,Date of Birth,Date of Joining,Department
EMP001,John Doe,Johnny,john.doe@example.com,1992-05-14,2020-03-01,Engineering
EMP002,Priya Sharma,Priya,priya.sharma@example.com,1995-10-22,2022-06-15,Marketing
EMP003,Alex Mercer,Alex,alex.mercer@example.com,1988-12-05,2018-09-10,Product Design`;

    const blob = new Blob([sampleCsv], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.setAttribute('href', url);
    link.setAttribute('download', 'employees_sample_template.csv');
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  const handleUpload = async () => {
    if (!selectedFile) return;
    setUploading(true);
    try {
      const res: CsvImportResponse = await api.uploadEmployeesCsv(selectedFile);
      setResult(res);
      if (res.imported > 0 || res.updated > 0) {
        toast.success(
          'CSV Processed',
          `Imported ${res.imported} new and updated ${res.updated} employee records.`
        );
        onSuccess();
      } else if (res.failed > 0) {
        toast.error('Import Failed', `All ${res.failed} rows had validation errors.`);
      }
    } catch (err: any) {
      toast.error('Upload Error', err.message || 'Failed to parse CSV file.');
    } finally {
      setUploading(false);
    }
  };

  const handleReset = () => {
    setSelectedFile(null);
    setResult(null);
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title="Bulk Import Employee Roster (CSV)"
      maxWidth="lg"
    >
      <div className="space-y-5 text-xs">
        {/* Info & Sample Download */}
        <div className="p-3.5 rounded-xl bg-slate-50 border border-slate-200/80 flex items-start justify-between gap-3">
          <div>
            <p className="font-semibold text-slate-800">Supported CSV Columns:</p>
            <p className="text-slate-500 text-[11px] mt-0.5 leading-relaxed">
              <code>Employee ID</code>, <code>Full Name</code>, <code>Email</code>,{' '}
              <code>Date of Birth</code> (YYYY-MM-DD or DD/MM/YYYY), <code>Date of Joining</code>,{' '}
              <code>Department</code>.
            </p>
          </div>
          <button
            type="button"
            onClick={handleDownloadSample}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-slate-300 bg-white hover:bg-slate-50 text-slate-700 font-semibold shrink-0 transition-colors"
          >
            <Download className="w-3.5 h-3.5 text-rose-500" />
            <span>Sample CSV</span>
          </button>
        </div>

        {/* Dropzone */}
        {!result ? (
          <div
            onClick={() => fileInputRef.current?.click()}
            className={`border-2 border-dashed rounded-2xl p-8 text-center cursor-pointer transition-colors ${
              selectedFile
                ? 'border-rose-400 bg-rose-50/20'
                : 'border-slate-200 hover:border-slate-300 bg-slate-50/50'
            }`}
          >
            <input
              ref={fileInputRef}
              type="file"
              accept=".csv,text/csv"
              onChange={handleFileChange}
              className="hidden"
            />
            {selectedFile ? (
              <div className="flex flex-col items-center gap-2">
                <FileText className="w-10 h-10 text-rose-500" />
                <div>
                  <p className="font-semibold text-slate-800">{selectedFile.name}</p>
                  <p className="text-[11px] text-slate-500">
                    {(selectedFile.size / 1024).toFixed(1)} KB — Click to choose a different file
                  </p>
                </div>
              </div>
            ) : (
              <div className="flex flex-col items-center gap-2">
                <UploadCloud className="w-10 h-10 text-slate-400" />
                <div>
                  <p className="font-semibold text-slate-700">Click to select or drag and drop your CSV</p>
                  <p className="text-[11px] text-slate-400 mt-0.5">Maximum file size: 5 MB</p>
                </div>
              </div>
            )}
          </div>
        ) : (
          /* Result Summary */
          <div className="space-y-4">
            <div className="grid grid-cols-3 gap-3">
              <div className="p-3.5 rounded-xl bg-emerald-50 border border-emerald-200 text-center">
                <p className="text-xl font-extrabold text-emerald-700">{result.imported}</p>
                <p className="text-[11px] font-semibold text-emerald-600">New Imported</p>
              </div>
              <div className="p-3.5 rounded-xl bg-sky-50 border border-sky-200 text-center">
                <p className="text-xl font-extrabold text-sky-700">{result.updated}</p>
                <p className="text-[11px] font-semibold text-sky-600">Updated</p>
              </div>
              <div className="p-3.5 rounded-xl bg-rose-50 border border-rose-200 text-center">
                <p className="text-xl font-extrabold text-rose-700">{result.failed}</p>
                <p className="text-[11px] font-semibold text-rose-600">Errors</p>
              </div>
            </div>

            {/* Error Breakdown Table */}
            {result.errors.length > 0 && (
              <div className="rounded-xl border border-rose-200 bg-rose-50/40 p-3 space-y-2 max-h-48 overflow-y-auto">
                <p className="font-bold text-rose-900 flex items-center gap-1.5">
                  <AlertCircle className="w-4 h-4 text-rose-600" />
                  <span>Validation Issues ({result.errors.length} rows skipped)</span>
                </p>
                <div className="space-y-1 text-[11px]">
                  {result.errors.map((err, i) => (
                    <div key={i} className="flex items-start gap-2 text-rose-800">
                      <span className="font-semibold bg-rose-200/80 px-1.5 py-0.5 rounded text-[10px]">
                        Row {err.row}
                      </span>
                      <span>{err.error}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        {/* Modal Actions */}
        <div className="flex justify-end gap-2 pt-3 border-t border-slate-100">
          {result ? (
            <button
              type="button"
              onClick={handleReset}
              className="px-4 py-2 rounded-xl border border-slate-200 text-slate-700 font-semibold hover:bg-slate-100 transition-colors"
            >
              Upload Another CSV
            </button>
          ) : (
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 rounded-xl border border-slate-200 text-slate-700 font-semibold hover:bg-slate-100 transition-colors"
            >
              Cancel
            </button>
          )}

          {!result && (
            <button
              type="button"
              disabled={!selectedFile || uploading}
              onClick={handleUpload}
              className="inline-flex items-center gap-1.5 px-5 py-2 rounded-xl bg-slate-900 hover:bg-slate-800 text-white font-semibold shadow-sm transition-colors disabled:opacity-50"
            >
              <UploadCloud className={`w-4 h-4 ${uploading ? 'animate-spin' : ''}`} />
              <span>{uploading ? 'Processing...' : 'Upload & Import'}</span>
            </button>
          )}
        </div>
      </div>
    </Modal>
  );
};
