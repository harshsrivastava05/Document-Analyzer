// frontend/src/lib/api.ts
const BASE = process.env.NEXT_PUBLIC_BACKEND_URL || "http://127.0.0.1:8000";

console.log('🔗 Backend URL configured as:', BASE);

export async function proxy(path: string, init?: RequestInit) {
  // Ensure path starts with /
  const normalizedPath = path.startsWith('/') ? path : `/${path}`;
  const url = `${BASE}${normalizedPath}`;
  
  console.log('📡 Proxying request to:', url);
  
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

    console.log('📨 Backend response:', response.status, response.statusText);
    clearTimeout(timeoutId);
    return response;
  } catch (error) {
    clearTimeout(timeoutId);
    console.error('❌ Backend request failed:', error);
    
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
    console.log('🏥 Backend health check:', response.ok ? 'healthy' : 'unhealthy');
    return response.ok;
  } catch (error) {
    console.error('🏥 Backend health check failed:', error);
    return false;
  }
}

// Enhanced health check with details
export async function getBackendHealth(): Promise<{ healthy: boolean; details?: any }> {
  try {
    const response = await fetch(`${BASE}/health`, { 
      method: 'GET',
      signal: AbortSignal.timeout(5000)
    });
    
    if (response.ok) {
      const data = await response.json();
      return { healthy: true, details: data };
    }
    
    return { healthy: false, details: { status: response.status } };
  } catch (error) {
    return { healthy: false, details: { error: error instanceof Error ? error.message : 'Unknown error' } };
  }
}

// Direct API call helper (for bypassing Next.js API routes)
export async function directBackendCall(endpoint: string, options?: RequestInit) {
  const normalizedEndpoint = endpoint.startsWith('/') ? endpoint : `/${endpoint}`;
  const url = `${BASE}${normalizedEndpoint}`;
  
  return fetch(url, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...options?.headers,
    },
    signal: options?.signal || AbortSignal.timeout(10000),
  });
}