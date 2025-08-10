"use client";

import useSWR from "swr";
import Link from "next/link";

const fetcher = (url: string) => fetch(url).then((r) => r.json());

export default function DashboardClient() {
  const { data, error, isLoading } = useSWR("/api/proxy/documents", fetcher);

  return (
    <div className="max-w-6xl mx-auto py-12 px-6">
      <h2 className="text-3xl font-bold mb-6">Your documents</h2>
      {isLoading && <p className="text-gray-400">Loading...</p>}
      {error && <p className="text-red-400">Failed to load documents.</p>}
      <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-6">
        {(data?.documents || []).map((doc: any) => (
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
    </div>
  );
}
