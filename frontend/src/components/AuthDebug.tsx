"use client";

import { useSession } from "next-auth/react";

export default function AuthDebug() {
  const { data: session, status } = useSession();

  // Only show in development
  if (process.env.NODE_ENV !== "development") return null;

  return (
    <div className="fixed bottom-4 right-4 bg-black/80 text-white p-4 rounded text-xs max-w-sm z-50">
      <div><strong>Status:</strong> {status}</div>
      <div><strong>Session:</strong> {session ? "✅" : "❌"}</div>
      {session && (
        <>
          <div><strong>User ID:</strong> {session.user?.id || "undefined"}</div>
          <div><strong>Email:</strong> {session.user?.email || "undefined"}</div>
        </>
      )}
    </div>
  );
}