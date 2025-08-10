const BASE = process.env.NEXT_PUBLIC_BACKEND_URL || "http://127.0.0.1:8000";

export async function proxy(path: string, init?: RequestInit) {
  const url = `${BASE}${path}`;
  return fetch(url, {
    ...init,
    credentials: "include",
  });
}
