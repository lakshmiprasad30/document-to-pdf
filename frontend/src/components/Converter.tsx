"use client";

import React, { useState, useRef, useEffect } from "react";
import { Upload, FileText, Download, Loader2, CheckCircle, AlertCircle, X, Layers } from "lucide-react";
import { uploadJob, getJobStatus, getDownloadUrl, uploadMergeJob } from "@/lib/api";

type UIState = "idle" | "uploading" | "queued" | "processing" | "completed" | "failed";

interface FileItem {
  id: string;
  file: File;
  uiState: UIState;
  jobId: string | null;
  resultId: string | null;
  errorMsg: string | null;
}

const SUPPORTED_EXTS = [".docx", ".xlsx", ".pptx", ".jpg", ".jpeg", ".png", ".webp", ".txt"];

export default function Converter() {
  const [files, setFiles] = useState<FileItem[]>([]);
  const [globalError, setGlobalError] = useState<string | null>(null);
  const [mergeState, setMergeState] = useState<UIState>("idle");
  const [mergeResultId, setMergeResultId] = useState<string | null>(null);
  
  const fileInputRef = useRef<HTMLInputElement>(null);
  const pollIntervalsRef = useRef<{ [key: string]: NodeJS.Timeout }>({});
  const mergePollIntervalRef = useRef<NodeJS.Timeout | null>(null);

  useEffect(() => {
    return () => {
      Object.values(pollIntervalsRef.current).forEach(clearInterval);
      if (mergePollIntervalRef.current) clearInterval(mergePollIntervalRef.current);
    };
  }, []);

  const handleFileSelect = (selectedFiles: FileList | File[]) => {
    setGlobalError(null);
    const newFiles: FileItem[] = [];
    
    Array.from(selectedFiles).forEach(file => {
      const ext = file.name.substring(file.name.lastIndexOf(".")).toLowerCase();
      if (!SUPPORTED_EXTS.includes(ext)) {
        setGlobalError(`Unsupported file type: ${file.name}`);
        return;
      }
      if (file.size > 50 * 1024 * 1024) {
        setGlobalError(`File size exceeds 50MB: ${file.name}`);
        return;
      }
      
      newFiles.push({
        id: Math.random().toString(36).substring(7),
        file,
        uiState: "idle",
        jobId: null,
        resultId: null,
        errorMsg: null,
      });
    });

    setFiles(prev => [...prev, ...newFiles]);
  };

  const onDrop = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      handleFileSelect(e.dataTransfer.files);
    }
  };

  const onFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      handleFileSelect(e.target.files);
    }
    if (fileInputRef.current) fileInputRef.current.value = "";
  };

  const updateFile = (id: string, updates: Partial<FileItem>) => {
    setFiles(prev => prev.map(f => f.id === id ? { ...f, ...updates } : f));
  };

  const removeFile = (id: string) => {
    if (pollIntervalsRef.current[id]) {
      clearInterval(pollIntervalsRef.current[id]);
      delete pollIntervalsRef.current[id];
    }
    setFiles(prev => prev.filter(f => f.id !== id));
  };

  const startPolling = (fileId: string, jobId: string) => {
    if (pollIntervalsRef.current[fileId]) clearInterval(pollIntervalsRef.current[fileId]);
    
    pollIntervalsRef.current[fileId] = setInterval(async () => {
      try {
        const statusRes = await getJobStatus(jobId);
        if (statusRes.status === "completed") {
          clearInterval(pollIntervalsRef.current[fileId]);
          updateFile(fileId, { uiState: "completed", resultId: statusRes.result_id || null });
        } else if (statusRes.status === "failed") {
          clearInterval(pollIntervalsRef.current[fileId]);
          updateFile(fileId, { uiState: "failed", errorMsg: statusRes.error || "Conversion failed" });
        } else if (statusRes.status === "processing") {
          updateFile(fileId, { uiState: "processing" });
        }
      } catch (err) {
        console.warn("Polling error:", err);
      }
    }, 2000);
  };

  const handleUploadAll = async () => {
    const idleFiles = files.filter(f => f.uiState === "idle" || f.uiState === "failed");
    for (const f of idleFiles) {
      updateFile(f.id, { uiState: "uploading", errorMsg: null });
      try {
        const res = await uploadJob(f.file);
        updateFile(f.id, { jobId: res.job_id, uiState: "queued" });
        startPolling(f.id, res.job_id);
      } catch (err: unknown) {
        updateFile(f.id, { uiState: "failed", errorMsg: err instanceof Error ? err.message : "Upload failed" });
      }
    }
  };

  const handleMerge = async () => {
    const completedFiles = files.filter(f => f.uiState === "completed" && f.resultId);
    if (completedFiles.length < 2) return;

    setMergeState("uploading");
    setMergeResultId(null);
    try {
      const pdfFiles: File[] = [];
      for (const f of completedFiles) {
        const res = await fetch(getDownloadUrl(f.resultId!));
        const blob = await res.blob();
        pdfFiles.push(new File([blob], `${f.file.name}.pdf`, { type: "application/pdf" }));
      }
      
      const res = await uploadMergeJob(pdfFiles);
      setMergeState("queued");
      
      if (mergePollIntervalRef.current) clearInterval(mergePollIntervalRef.current);
      mergePollIntervalRef.current = setInterval(async () => {
        try {
          const statusRes = await getJobStatus(res.job_id);
          if (statusRes.status === "completed") {
             clearInterval(mergePollIntervalRef.current!);
             setMergeState("completed");
             setMergeResultId(statusRes.result_id || null);
          } else if (statusRes.status === "failed") {
             clearInterval(mergePollIntervalRef.current!);
             setMergeState("failed");
             setGlobalError(statusRes.error || "Merge failed");
          } else {
             setMergeState(statusRes.status as UIState);
          }
        } catch(e) {}
      }, 2000);

    } catch(err: unknown) {
      setMergeState("failed");
      setGlobalError(err instanceof Error ? err.message : "Merge failed");
    }
  };

  return (
    <div className="w-full max-w-3xl mx-auto p-6 bg-white rounded-xl shadow-lg border border-gray-100">
      
      {globalError && (
        <div className="mb-6 p-4 bg-red-50 text-red-700 rounded-lg flex items-start gap-3">
          <AlertCircle className="shrink-0 mt-0.5" size={20} />
          <p className="text-sm">{globalError}</p>
          <button onClick={() => setGlobalError(null)} className="ml-auto text-red-400 hover:text-red-700">
            <X size={20} />
          </button>
        </div>
      )}

      {/* DROPZONE */}
      <div 
        className="border-2 border-dashed rounded-xl p-8 flex flex-col items-center justify-center text-center transition-colors border-blue-200 bg-blue-50/50 hover:bg-blue-50 mb-6"
        onDragOver={(e) => e.preventDefault()}
        onDrop={onDrop}
      >
        <input 
          type="file" 
          multiple
          accept=".docx,.xlsx,.pptx,.jpg,.jpeg,.png,.webp,.txt" 
          className="hidden" 
          ref={fileInputRef}
          onChange={onFileChange}
        />
        <div className="mb-4 text-blue-500 bg-blue-100 p-4 rounded-full">
          <Upload size={32} />
        </div>
        <h3 className="text-lg font-semibold mb-2 text-gray-800">
          Drag & drop your files here
        </h3>
        <button 
          onClick={() => fileInputRef.current?.click()}
          className="px-5 py-2 mt-2 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700 transition-colors"
        >
          Choose Files
        </button>
        <p className="mt-4 text-xs text-gray-500">
          Supported: DOCX, XLSX, PPTX, JPG, PNG, WEBP, TXT (Max 50MB)
        </p>
      </div>

      {/* FILE LIST */}
      {files.length > 0 && (
        <div className="space-y-3 mb-6">
          <h4 className="font-semibold text-gray-700">Files ({files.length})</h4>
          {files.map(f => (
            <div key={f.id} className="p-4 bg-gray-50 rounded-lg border border-gray-200 flex items-center gap-4">
              <FileText className="text-blue-500 shrink-0" size={24} />
              <div className="flex-1 min-w-0">
                <p className="truncate font-medium text-gray-800 text-sm">{f.file.name}</p>
                <div className="flex items-center gap-2 mt-1">
                  {f.uiState === "idle" && <span className="text-xs text-gray-500">Ready</span>}
                  {f.uiState === "uploading" && <span className="text-xs text-blue-500 flex items-center gap-1"><Loader2 size={12} className="animate-spin" /> Uploading...</span>}
                  {f.uiState === "queued" && <span className="text-xs text-purple-500">Queued</span>}
                  {f.uiState === "processing" && <span className="text-xs text-orange-500 flex items-center gap-1"><Loader2 size={12} className="animate-spin" /> Converting...</span>}
                  {f.uiState === "completed" && <span className="text-xs text-green-600 flex items-center gap-1"><CheckCircle size={12} /> Done</span>}
                  {f.uiState === "failed" && <span className="text-xs text-red-500 truncate" title={f.errorMsg || ""}>{f.errorMsg}</span>}
                </div>
              </div>
              <div className="flex gap-2">
                {f.uiState === "completed" && f.resultId && (
                  <a href={getDownloadUrl(f.resultId)} download className="p-2 text-blue-600 hover:bg-blue-100 rounded-md" title="Download">
                    <Download size={18} />
                  </a>
                )}
                {["idle", "completed", "failed"].includes(f.uiState) && (
                  <button onClick={() => removeFile(f.id)} className="p-2 text-gray-400 hover:text-red-500 hover:bg-red-50 rounded-md" title="Remove">
                    <X size={18} />
                  </button>
                )}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* ACTIONS */}
      {files.length > 0 && (
        <div className="flex flex-wrap gap-4 border-t pt-6">
          <button 
            onClick={handleUploadAll}
            disabled={!files.some(f => f.uiState === "idle" || f.uiState === "failed")}
            className="px-6 py-2.5 bg-blue-600 text-white font-medium rounded-lg hover:bg-blue-700 disabled:opacity-50 transition-colors"
          >
            Convert All
          </button>
          
          {files.filter(f => f.uiState === "completed").length >= 2 && (
            <button 
              onClick={handleMerge}
              disabled={mergeState === "uploading" || mergeState === "queued" || mergeState === "processing"}
              className="flex items-center gap-2 px-6 py-2.5 bg-purple-600 text-white font-medium rounded-lg hover:bg-purple-700 disabled:opacity-50 transition-colors"
            >
              <Layers size={18} />
              {mergeState === "idle" || mergeState === "completed" || mergeState === "failed" ? "Merge PDFs" : "Merging..."}
            </button>
          )}

          {mergeState === "completed" && mergeResultId && (
            <a 
              href={getDownloadUrl(mergeResultId)}
              download="merged_documents.pdf"
              className="flex items-center gap-2 px-6 py-2.5 bg-green-600 text-white font-medium rounded-lg hover:bg-green-700 transition-colors"
            >
              <Download size={18} />
              Download Merged PDF
            </a>
          )}
        </div>
      )}
    </div>
  );
}
