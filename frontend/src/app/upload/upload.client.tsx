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
      setStatus("Uploading...");
      const form = new FormData();
      form.append("file", file);
      const res = await fetch("/api/proxy/upload", {
        method: "POST",
        body: form,
      });

      if (!res.ok) throw new Error("Upload failed" + res.statusText);
      const data = await res.json();
      setStatus("Uploaded and queued for analysis.");
    } catch (e: any) {
      setStatus(e.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-3xl mx-auto py-12 px-6">
      <div className="rounded-2xl border border-white/10 bg-white/5 p-8">
        <h2 className="text-2xl font-semibold mb-4">Upload a document</h2>
        <p className="text-gray-400 mb-6">
          PDF, DOCX, or TXT. Files are stored in your Google Drive folder and
          analyzed with Gemini + RAG. Only available when signed in.
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
        {status && <p className="mt-4 text-sm text-gray-300">{status}</p>}
      </div>
    </div>
  );
}
