"use client";

import useSWR from "swr";
import Link from "next/link";

const fetcher = (url: string) => fetch(url).then((r) => r.json());

export default function DashboardClient() {
  const { data, error, isLoading } = useSWR("/api/proxy/documents", fetcher);

  const documents = data?.documents || [];
  const hasDocuments = documents.length > 0;

  return (
    <div className="max-w-6xl mx-auto py-12 px-6">
      <h2 className="text-3xl font-bold mb-6">Your documents</h2>

      {isLoading && <p className="text-gray-400">Loading...</p>}
      {error && <p className="text-red-400">Failed to load documents.</p>}

      {hasDocuments ? (
        <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-6">
          {documents.map((doc: any) => (
            <Link
              key={doc.id}
              href={`/chat/${doc.id}`}
              className="rounded-xl border border-white/10 bg-white/5 p-5 hover:border-violet-500 transition"
            >
              <div className="text-lg font-semibold">
                {doc.title || "Untitled"}
              </div>
              <div className="text-xs text-gray-400 mt-1">
                {new Date(doc.createdAt).toLocaleString()}
              </div>
              <div className="text-sm text-gray-300 mt-3 line-clamp-3">
                {doc.summary || "Click to open chat"}
              </div>
            </Link>
          ))}
        </div>
      ) : (
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
      )}
    </div>
  );
}
