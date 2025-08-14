// frontend/src/lib/api.ts
const BASE = process.env.NEXT_PUBLIC_BACKEND_URL || "http://127.0.0.1:8000";

export async function proxy(path: string, init?: RequestInit) {
  const url = `${BASE}${path}`;
  
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), 30000); // 30 second timeout

  try {
    const response = await fetch(url, {
      ...init,
      credentials: "include",
      signal: controller.signal,
      headers: {
        'Content-Type': 'application/json',
        ...init?.headers,
      },
    });

    clearTimeout(timeoutId);
    return response;
  } catch (error) {
    clearTimeout(timeoutId);
    
    if (error instanceof Error) {
      if (error.name === 'AbortError') {
        throw new Error('Request timeout - backend server may be down');
      }
      throw new Error(`Backend connection failed: ${error.message}`);
    }
    throw error;
  }
}

// Helper function to check if backend is available
export async function healthCheck(): Promise<boolean> {
  try {
    const response = await fetch(`${BASE}/health`, { 
      method: 'GET',
      signal: AbortSignal.timeout(5000) // 5 second timeout for health check
    });
    return response.ok;
  } catch {
    return false;
  }
}