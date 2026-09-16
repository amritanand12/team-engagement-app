import React, { useEffect, useState, useRef } from 'react';
import { api } from '../api/client';
import { PublicPhotoInfo } from '../types';
import {
  Sparkles,
  Upload,
  CheckCircle2,
  AlertCircle,
  Camera,
  Image as ImageIcon,
  Loader2,
  PartyPopper,
  ArrowLeft,
} from 'lucide-react';

export const PhotoUploadPortal: React.FC = () => {
  const [token, setToken] = useState<string | null>(null);
  const [info, setInfo] = useState<PublicPhotoInfo | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // File upload state
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [uploading, setUploading] = useState(false);
  const [uploadSuccess, setUploadSuccess] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    const query = new URLSearchParams(window.location.search);
    const t = query.get('token');
    if (!t) {
      setError('Invalid or missing photo submission token. Please use the personalized link sent to your email.');
      setLoading(false);
      return;
    }
    setToken(t);

    api.getPublicPhotoInfo(t)
      .then((data) => {
        setInfo(data);
        if (data.current_photo_url && data.has_custom_photo) {
          setPreviewUrl(data.current_photo_url.startsWith('http') ? data.current_photo_url : `http://localhost:8000${data.current_photo_url}`);
        }
      })
      .catch((err) => {
        setError(err.message || 'Unable to load photo upload details.');
      })
      .finally(() => {
        setLoading(false);
      });
  }, []);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      const file = e.target.files[0];
      setSelectedFile(file);
      const url = URL.createObjectURL(file);
      setPreviewUrl(url);
    }
  };

  const handleDrop = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      const file = e.dataTransfer.files[0];
      setSelectedFile(file);
      const url = URL.createObjectURL(file);
      setPreviewUrl(url);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!token || !selectedFile) return;

    setUploading(true);
    setError(null);
    try {
      const res = await api.uploadPublicPhoto(token, selectedFile);
      setUploadSuccess(true);
      if (res.photo_url) {
        setPreviewUrl(res.photo_url.startsWith('http') ? res.photo_url : `http://localhost:8000${res.photo_url}`);
      }
    } catch (err: any) {
      setError(err.message || 'Failed to upload photo. Please try again.');
    } finally {
      setUploading(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-slate-950 text-slate-100 flex items-center justify-center p-4">
        <div className="flex flex-col items-center gap-3">
          <Loader2 className="w-8 h-8 text-rose-500 animate-spin" />
          <p className="text-sm text-slate-400">Loading celebration details...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex items-center justify-center p-4 sm:p-6 relative overflow-hidden select-none">
      {/* Background glow effects */}
      <div className="fixed top-1/4 left-1/4 w-[36rem] h-[36rem] bg-rose-600/10 rounded-full blur-[140px] pointer-events-none" />
      <div className="fixed bottom-1/4 right-1/4 w-[36rem] h-[36rem] bg-indigo-600/10 rounded-full blur-[140px] pointer-events-none" />

      <div className="w-full max-w-lg relative z-10 mx-auto">
        {/* Header */}
        <div className="text-center mb-6">
          {info?.company_logo_url ? (
            <img
              src={info.company_logo_url}
              alt={info.company_name}
              className="h-10 mx-auto mb-3 object-contain"
            />
          ) : (
            <div className="inline-flex items-center justify-center p-3 bg-gradient-to-tr from-rose-500/20 to-indigo-500/20 border border-rose-500/30 rounded-2xl shadow-xl mb-3">
              <Camera className="w-7 h-7 text-rose-400" />
            </div>
          )}
          <h1 className="text-2xl sm:text-3xl font-extrabold text-white tracking-tight">
            Celebration Photo Submission
          </h1>
          <p className="text-xs sm:text-sm text-slate-400 mt-1">
            {info?.company_name || 'Team Engagement Portal'}
          </p>
        </div>

        {/* Card */}
        <div className="bg-slate-900/90 backdrop-blur-2xl border border-slate-800 rounded-3xl shadow-2xl p-7 sm:p-9 relative overflow-hidden">
          {error && (
            <div className="mb-5 p-4 rounded-xl bg-rose-500/10 border border-rose-500/30 text-rose-300 text-xs flex items-start gap-2.5">
              <AlertCircle className="w-4 h-4 flex-shrink-0 mt-0.5 text-rose-400" />
              <span className="leading-relaxed">{error}</span>
            </div>
          )}

          {uploadSuccess ? (
            <div className="text-center py-6 space-y-4">
              <div className="inline-flex p-4 rounded-full bg-emerald-500/15 border border-emerald-500/30 text-emerald-400">
                <PartyPopper className="w-10 h-10" />
              </div>
              <h2 className="text-xl font-bold text-white">Photo Saved Successfully!</h2>
              <p className="text-sm text-slate-300 max-w-sm mx-auto leading-relaxed">
                Thank you, <strong>{info?.preferred_name || info?.employee_name}</strong>! Your chosen picture has been saved and will be featured in your upcoming celebration announcement.
              </p>

              {previewUrl && (
                <div className="mt-4 inline-block relative rounded-2xl overflow-hidden border-2 border-rose-500/50 shadow-xl">
                  <img
                    src={previewUrl}
                    alt="Celebration Photo Preview"
                    className="w-40 h-40 object-cover"
                  />
                </div>
              )}

              <div className="pt-4">
                <button
                  type="button"
                  onClick={() => setUploadSuccess(false)}
                  className="text-xs text-rose-400 hover:text-rose-300 underline font-medium cursor-pointer"
                >
                  Want to upload a different photo instead?
                </button>
              </div>
            </div>
          ) : (
            <form onSubmit={handleSubmit} className="space-y-5">
              <div>
                {info?.expires_at && (
                  <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-slate-800/90 border border-slate-700 text-[11px] text-amber-300 mb-3 shadow-xs">
                    <span>⏳ Link valid until {new Date(info.expires_at).toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' })} (7 days)</span>
                  </div>
                )}
                <p className="text-sm text-slate-300 mb-1">
                  Hi <strong className="text-white">{info?.preferred_name || info?.employee_name}</strong>,
                </p>
                <p className="text-xs text-slate-400 leading-relaxed">
                  Please choose a photo of yourself (such as a favorite portrait, vacation snapshot, or friendly moment) to feature in your celebratory email and company digest.
                </p>
              </div>

              {/* Drag and drop upload zone */}
              <div
                onDragOver={(e) => e.preventDefault()}
                onDrop={handleDrop}
                onClick={() => fileInputRef.current?.click()}
                className="border-2 border-dashed border-slate-700 hover:border-rose-500/60 rounded-2xl p-6 text-center cursor-pointer transition-colors bg-slate-950/50 group"
              >
                <input
                  ref={fileInputRef}
                  type="file"
                  accept="image/jpeg,image/png,image/webp,image/gif"
                  onChange={handleFileChange}
                  className="hidden"
                />

                {previewUrl ? (
                  <div className="flex flex-col items-center gap-3">
                    <img
                      src={previewUrl}
                      alt="Selected Preview"
                      className="w-32 h-32 object-cover rounded-2xl border-2 border-rose-500/60 shadow-lg shadow-rose-950/40"
                    />
                    <p className="text-xs text-slate-400">
                      {selectedFile ? selectedFile.name : 'Current Photo'} — <span className="text-rose-400 group-hover:underline">Click to change</span>
                    </p>
                  </div>
                ) : (
                  <div className="flex flex-col items-center gap-2.5 py-4">
                    <div className="p-3 bg-rose-500/10 rounded-2xl text-rose-400 group-hover:scale-110 transition-transform">
                      <Upload className="w-6 h-6" />
                    </div>
                    <div>
                      <p className="text-xs font-semibold text-white">Click or drag & drop your photo</p>
                      <p className="text-[11px] text-slate-500 mt-1">Supports JPG, PNG, WEBP, or GIF (max 10MB)</p>
                    </div>
                  </div>
                )}
              </div>

              <button
                type="submit"
                disabled={!selectedFile || uploading}
                className="w-full py-3 px-4 bg-gradient-to-r from-rose-500 to-indigo-600 hover:from-rose-600 hover:to-indigo-700 disabled:opacity-40 disabled:cursor-not-allowed text-white font-semibold text-sm rounded-xl shadow-lg shadow-rose-950/50 flex items-center justify-center gap-2 transition-all cursor-pointer"
              >
                {uploading ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" />
                    <span>Saving Photo...</span>
                  </>
                ) : (
                  <>
                    <Sparkles className="w-4 h-4" />
                    <span>Submit Celebration Photo</span>
                  </>
                )}
              </button>

              <p className="text-center text-[11px] text-slate-500 pt-2">
                If no photo is submitted, the standard company avatar template will be used automatically.
              </p>
            </form>
          )}
        </div>
      </div>
    </div>
  );
};
