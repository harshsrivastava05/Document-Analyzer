// Add this to your frontend to debug JWT tokens
// components/JWTDebug.tsx
"use client";

import { useSession } from "next-auth/react";
import { createJWTForBackend } from "@/lib/jwt";
import { useState } from "react";

export default function JWTDebug() {
  const { data: session } = useSession();
  const [jwtDecoded, setJwtDecoded] = useState<any>(null);

  const debugJWT = () => {
    if (!session?.user?.id) {
      console.log("❌ No session or user ID");
      return;
    }

    console.log("🔍 Session data:", {
      id: session.user.id,
      email: session.user.email,
      name: session.user.name
    });

    const jwt = createJWTForBackend(session.user.id);
    console.log("🔑 Generated JWT:", jwt);

    // Decode JWT (client-side for debugging only)
    try {
      const payload = JSON.parse(atob(jwt.split('.')[1]));
      console.log("📄 JWT Payload:", payload);
      setJwtDecoded(payload);
    } catch (e) {
      console.error("Failed to decode JWT:", e);
    }
  };

  const testBackend = async () => {
    if (!session?.user?.id) return;

    try {
      console.log("🔧 Testing backend debug endpoint...");
      const response = await fetch(`/api/proxy/documents/debug/${session.user.id}`);
      const data = await response.json();
      console.log("🔍 Backend debug response:", data);
    } catch (error) {
      console.error("❌ Backend test failed:", error);
    }
  };

  if (!session) {
    return <div className="p-4 bg-yellow-100">Not authenticated</div>;
  }

  return (
    <div className="p-4 bg-gray-100 rounded-lg space-y-4">
      <h3 className="font-bold">JWT Debug Panel</h3>
      
      <div className="space-y-2">
        <p><strong>User ID:</strong> {session.user?.id}</p>
        <p><strong>Email:</strong> {session.user?.email}</p>
        <p><strong>Name:</strong> {session.user?.name}</p>
      </div>

      <div className="space-x-2">
        <button 
          onClick={debugJWT}
          className="px-4 py-2 bg-blue-500 text-white rounded"
        >
          Debug JWT
        </button>
        <button 
          onClick={testBackend}
          className="px-4 py-2 bg-green-500 text-white rounded"
        >
          Test Backend
        </button>
      </div>

      {jwtDecoded && (
        <div className="p-3 bg-gray-200 rounded">
          <h4 className="font-semibold">JWT Payload:</h4>
          <pre className="text-xs">{JSON.stringify(jwtDecoded, null, 2)}</pre>
        </div>
      )}
    </div>
  );
}