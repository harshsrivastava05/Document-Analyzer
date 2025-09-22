"use client";

import { useState } from "react";
import Button from "@/components/ui/Button";

export default function UploadClient() {
  const [file, setFile] = useState<File | null>(null);
  const [loading, setLoading] = useState(false);
  const [status, setStatus] = useState<string | null>(null);

  const handleUpload = async () => {
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
      setStatus("File uploaded successfully and queued for analysis.");
      setFile(null); // Reset file input
      
      // Reset file input element
      const fileInput = document.querySelector('input[type="file"]') as HTMLInputElement;
      if (fileInput) fileInput.value = '';
      
    } catch (e: any) {
      setStatus(`Error: ${e.message}`);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-3xl mx-auto py-12 px-6">
      <div className="rounded-2xl border border-white/10 bg-white/5 p-8">
        <h2 className="text-2xl font-semibold mb-4">Upload a document</h2>
        <p className="text-gray-400 mb-6">
          PDF, DOCX, or TXT files up to 10MB. Files are securely stored in Google Cloud Storage
          and analyzed with AI for question-answering. Only available when signed in.
        </p>
        <div className="flex items-center gap-4">
          <input
            type="file"
            accept=".pdf,.doc,.docx,.txt"
            onChange={(e) => setFile(e.target.files?.[0] || null)}
            className="block w-full text-sm file:mr-4 file:rounded-lg file:border-0 file:bg-violet-600 file:px-4 file:py-2 file:text-white hover:file:bg-violet-500"
          />
          <Button onClick={handleUpload} disabled={!file || loading}>
            {loading ? "Uploading..." : "Upload"}
          </Button>
        </div>
        {status && (
          <p className={`mt-4 text-sm ${
            status.includes('Error') ? 'text-red-400' : 'text-gray-300'
          }`}>
            {status}
          </p>
        )}
        {file && (
          <div className="mt-4 text-sm text-gray-400">
            Selected: {file.name} ({(file.size / 1024 / 1024).toFixed(2)} MB)
          </div>
        )}
      </div>
    </div>
  );
}