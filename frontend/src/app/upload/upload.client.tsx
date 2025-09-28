"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Button from "@/components/ui/Button";

type UploadMode = 'gcs-direct' | 'backend-proxy';

export default function UploadClient() {
  const [file, setFile] = useState<File | null>(null);
  const [loading, setLoading] = useState(false);
  const [status, setStatus] = useState<string | null>(null);
  const [uploadMode, setUploadMode] = useState<UploadMode>('backend-proxy');
  const router = useRouter();

  const handleUploadDirect = async () => {
    if (!file) return;
    
    try {
      setLoading(true);
      setStatus("Uploading to Google Cloud Storage...");
      
      const form = new FormData();
      form.append("file", file);
      
      const res = await fetch("/api/upload-gcs", {
        method: "POST",
        body: form,
      });

      if (!res.ok) {
        const errorData = await res.json();
        throw new Error(errorData.error || "Upload failed");
      }
      
      const data = await res.json();
      setStatus("File uploaded successfully! Redirecting to chat...");
      
      // Wait a moment and then redirect to the chat page
      setTimeout(() => {
        router.push(`/chat/${data.document.id}`);
      }, 2000);
      
    } catch (e: any) {
      setStatus(`Error: ${e.message}`);
    } finally {
      setLoading(false);
    }
  };

  const handleUploadViaBackend = async () => {
    if (!file) return;
    
    try {
      setLoading(true);
      setStatus("Uploading via backend with AI processing...");
      
      const form = new FormData();
      form.append("file", file);
      
      const res = await fetch("/api/proxy/upload", {
        method: "POST",
        body: form,
      });

      if (!res.ok) {
        const errorData = await res.json();
        throw new Error(errorData.error || "Backend upload failed");
      }
      
      const data = await res.json();
      setStatus(`File uploaded and processed successfully! Redirecting to chat...`);
      
      // Wait a moment to show success message, then redirect
      setTimeout(() => {
        router.push(`/chat/${data.document.id}`);
      }, 2000);
      
    } catch (e: any) {
      setStatus(`Backend Error: ${e.message}`);
      
      // Fallback to direct upload if backend is down
      if (e.message.includes('Backend service unavailable') || 
          e.message.includes('Unable to connect to backend')) {
        setStatus("Backend unavailable, trying direct upload...");
        await handleUploadDirect();
      }
    } finally {
      setLoading(false);
    }
  };

  const resetForm = () => {
    setFile(null);
    // Reset file input element
    const fileInput = document.querySelector('input[type="file"]') as HTMLInputElement;
    if (fileInput) fileInput.value = '';
  };

  const handleUpload = async () => {
    if (uploadMode === 'gcs-direct') {
      await handleUploadDirect();
    } else {
      await handleUploadViaBackend();
    }
  };

  return (
    <div className="max-w-3xl mx-auto py-12 px-6">
      <div className="rounded-2xl border border-white/10 bg-white/5 p-8">
        <h2 className="text-2xl font-semibold mb-4">Upload a document</h2>
        <p className="text-gray-400 mb-6">
          PDF, DOCX, or TXT files up to 10MB. Files are securely stored and analyzed with AI.
        </p>
        
        {/* Upload Mode Toggle */}
        <div className="mb-4">
          <label className="text-sm text-gray-400 mb-2 block">Upload Method:</label>
          <div className="flex gap-4">
            <label className="flex items-center gap-2">
              <input
                type="radio"
                name="uploadMode"
                value="backend-proxy"
                checked={uploadMode === 'backend-proxy'}
                onChange={(e) => setUploadMode(e.target.value as UploadMode)}
                className="text-violet-600"
              />
              <span className="text-sm">Backend Processing (Recommended)</span>
            </label>
            <label className="flex items-center gap-2">
              <input
                type="radio"
                name="uploadMode"
                value="gcs-direct"
                checked={uploadMode === 'gcs-direct'}
                onChange={(e) => setUploadMode(e.target.value as UploadMode)}
                className="text-violet-600"
              />
              <span className="text-sm">Direct Upload</span>
            </label>
          </div>
        </div>

        <div className="flex items-center gap-4">
          <input
            type="file"
            accept=".pdf,.doc,.docx,.txt"
            onChange={(e) => setFile(e.target.files?.[0] || null)}
            className="block w-full text-sm file:mr-4 file:rounded-lg file:border-0 file:bg-violet-600 file:px-4 file:py-2 file:text-white hover:file:bg-violet-500"
            disabled={loading}
          />
          <Button onClick={handleUpload} disabled={!file || loading}>
            {loading ? "Processing..." : "Upload"}
          </Button>
        </div>
        
        {status && (
          <div className={`mt-4 p-3 rounded-lg text-sm ${
            status.includes('Error') || status.includes('error') 
              ? 'bg-red-900/20 text-red-400 border border-red-800' 
              : status.includes('Redirecting')
              ? 'bg-blue-900/20 text-blue-400 border border-blue-800'
              : 'bg-green-900/20 text-green-400 border border-green-800'
          }`}>
            {status}
            {status.includes('Redirecting') && (
              <div className="mt-2">
                <div className="animate-spin inline-block w-4 h-4 border-2 border-current border-t-transparent rounded-full mr-2"></div>
                Taking you to the chat page...
              </div>
            )}
          </div>
        )}
        
        {file && !loading && (
          <div className="mt-4 p-3 bg-gray-900/50 rounded-lg">
            <div className="text-sm text-gray-300">
              <strong>Selected:</strong> {file.name}
            </div>
            <div className="text-xs text-gray-400">
              Size: {(file.size / 1024 / 1024).toFixed(2)} MB | Type: {file.type}
            </div>
          </div>
        )}

        <div className="mt-6 p-4 bg-blue-900/20 border border-blue-800 rounded-lg">
          <h3 className="text-sm font-medium text-blue-400 mb-2">Upload Methods Explained:</h3>
          <ul className="text-xs text-blue-200 space-y-1">
            <li><strong>Backend Processing:</strong> Full AI analysis, embeddings, and RAG capabilities</li>
            <li><strong>Direct Upload:</strong> Faster upload, limited backend processing (if backend is down)</li>
          </ul>
        </div>

        {/* Processing Information */}
        <div className="mt-4 p-4 bg-violet-900/20 border border-violet-800 rounded-lg">
          <h3 className="text-sm font-medium text-violet-400 mb-2">What happens after upload:</h3>
          <ul className="text-xs text-violet-200 space-y-1">
            <li>✨ AI analysis and summarization</li>
            <li>🔍 Text extraction and embedding creation</li>
            <li>💬 Ready for intelligent Q&A chat</li>
            <li>📱 Automatic redirect to chat interface</li>
          </ul>
        </div>
      </div>
    </div>
  );
}