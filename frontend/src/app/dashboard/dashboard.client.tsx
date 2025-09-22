"use client";

import useSWR from "swr";
import Link from "next/link";
import { useState } from "react";

const fetcher = (url: string) => fetch(url).then((r) => r.json());

export default function DashboardClient() {
  const { data, error, isLoading } = useSWR("/api/proxy/documents", fetcher);
  const [downloading, setDownloading] = useState<string | null>(null);

  const documents = data?.documents || [];
  const hasDocuments = documents.length > 0;

  const handleDownload = async (documentId: string, title: string) => {
    try {
      setDownloading(documentId);
      const response = await fetch(`/api/documents/${documentId}/download`);
      
      if (!response.ok) {
        throw new Error('Download failed');
      }

      // Get the blob and create download link
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.style.display = 'none';
      a.href = url;
      a.download = title || 'document';
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    } catch (error) {
      console.error('Download failed:', error);
      alert('Failed to download file');
    } finally {
      setDownloading(null);
    }
  };

  const formatFileSize = (bytes: number) => {
    if (!bytes) return 'Unknown size';
    const mb = bytes / (1024 * 1024);
    return `${mb.toFixed(2)} MB`;
  };

  return (
    <div className="max-w-6xl mx-auto py-12 px-6">
      <h2 className="text-3xl font-bold mb-6">Your documents</h2>

      {isLoading && <p className="text-gray-400">Loading...</p>}
      {error && <p className="text-red-400">Failed to load documents.</p>}

      {!isLoading && hasDocuments ? (
        <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-6">
          {documents.map((doc: any) => (
            <div
              key={doc.id}
              className="rounded-xl border border-white/10 bg-white/5 p-5 hover:border-violet-500 transition"
            >
              <div className="text-lg font-semibold mb-2">
                {doc.title || "Untitled"}
              </div>
              <div className="text-xs text-gray-400 mb-1">
                {new Date(doc.createdAt).toLocaleString()}
              </div>
              {doc.fileSize && (
                <div className="text-xs text-gray-400 mb-3">
                  {formatFileSize(doc.fileSize)}
                </div>
              )}
              <div className="text-sm text-gray-300 mb-4 line-clamp-3">
                {doc.summary || "Click to open chat"}
              </div>
              
              <div className="flex gap-2">
                <Link
                  href={`/chat/${doc.id}`}
                  className="flex-1 text-center px-3 py-2 bg-violet-600 hover:bg-violet-500 text-white rounded-lg text-sm transition"
                >
                  Chat
                </Link>
                <button
                  onClick={() => handleDownload(doc.id, doc.title)}
                  disabled={downloading === doc.id}
                  className="px-3 py-2 bg-white/10 hover:bg-white/20 text-white border border-white/10 rounded-lg text-sm transition disabled:opacity-50"
                >
                  {downloading === doc.id ? 'Downloading...' : 'Download'}
                </button>
              </div>
            </div>
          ))}
        </div>
      ) : (
        !isLoading && (
          <div className="flex flex-col items-center justify-center py-16 border-2 border-dashed border-violet-500/30 rounded-xl bg-gradient-to-br from-violet-500/10 to-transparent">
            <svg
              xmlns="http://www.w3.org/2000/svg"
              className="h-12 w-12 text-violet-400 mb-4"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
              strokeWidth={1.5}
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M12 4.5v15m7.5-7.5h-15"
              />
            </svg>
            <h3 className="text-lg font-semibold text-gray-200">
              Sorry, you have yet to upload a document
            </h3>
            <p className="text-gray-400 text-sm mt-1">
              Start by uploading your first document to see it here.
            </p>
            <Link
              href="/upload"
              className="mt-6 px-4 py-2 bg-violet-500 hover:bg-violet-600 text-white rounded-lg shadow-lg transition"
            >
              Upload Document
            </Link>
          </div>
        )
      )}
    </div>
  );
}